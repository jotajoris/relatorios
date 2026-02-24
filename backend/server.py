from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, status, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# Timezone de Brasília (UTC-3)
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

def now_brazil():
    """Retorna a data/hora atual no fuso horário de Brasília"""
    return datetime.now(BRAZIL_TZ)

def today_brazil():
    """Retorna a data atual no fuso horário de Brasília"""
    return datetime.now(BRAZIL_TZ).date()
import bcrypt
import jwt
import pandas as pd
from io import BytesIO

# Import Growatt service early for power curve endpoint
from services.growatt_service import get_growatt_oss_service, reset_growatt_oss_service

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration - key must be at least 32 bytes for HS256
JWT_SECRET = os.environ.get('JWT_SECRET', 'solar-energy-management-secret-key-2025-secure')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24
JWT_REFRESH_EXPIRATION_DAYS = 7

# Security
security = HTTPBearer()

# Create the main app
app = FastAPI(title="ON Soluções Energéticas - Solar Management API")

# Custom CORS Middleware - Forces CORS headers on ALL responses
class ForceCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            response = Response(status_code=204)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "3600"
            return response
        
        # Process the request
        response = await call_next(request)
        
        # Force CORS headers on ALL responses
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
        
        return response

# Add custom CORS middleware FIRST (executes last, so headers are always added)
app.add_middleware(ForceCORSMiddleware)

# Standard CORS middleware as backup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== HEALTH CHECK (must respond fast) ====================
@app.get("/health")
async def health_check():
    """Health check endpoint - responds immediately without DB check"""
    return {"status": "healthy", "service": "solar-management-api"}

@app.get("/api/health")
async def api_health_check():
    """API Health check endpoint"""
    return {"status": "healthy", "service": "solar-management-api"}

# ==================== MODELS ====================

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = "admin"

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class ClientBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    document: Optional[str] = None  # CPF/CNPJ
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    logo_url: Optional[str] = None
    contact_person: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class Client(ClientBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

class PlantBase(BaseModel):
    name: str
    client_id: str
    capacity_kwp: float
    installation_date: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = "PR"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    inverter_brand: Optional[str] = None
    monthly_prognosis_kwh: Optional[float] = None
    annual_prognosis_kwh: Optional[float] = None
    total_investment: Optional[float] = None
    logo_url: Optional[str] = None  # Logo específica da usina
    efficiency_loss_year1: Optional[float] = 2.5  # % perda 1º ano
    efficiency_loss_year2: Optional[float] = 1.5  # % perda 2º ano
    efficiency_loss_other: Optional[float] = 0.5  # % perda demais anos
    is_monitored: bool = True  # Usina ativa (monitorada)
    show_missing_reports_alert: bool = True  # Exibir alerta relatórios ausentes
    use_global_notifications: bool = True  # Usar config globais notificações
    notify_critical_state: bool = False  # Notificar estado crítico
    public_share_enabled: bool = False  # Permitir link compartilhamento
    public_share_token: Optional[str] = None  # Token compartilhamento

class PlantCreate(PlantBase):
    pass

class Plant(PlantBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    status: str = "online"

# Client Login Model for portal credentials
class ClientLoginBase(BaseModel):
    inverter_app: str  # Growatt, FusionSolar, Deye, etc
    on_unit: Optional[str] = None  # ON CWB, ON CG
    client_name: Optional[str] = None
    login: str
    password: str
    site_url: Optional[str] = None
    is_installer: bool = False

class ClientLoginCreate(ClientLoginBase):
    pass

class ClientLogin(ClientLoginBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConsumerUnitBase(BaseModel):
    plant_id: str
    uc_number: str  # Número da UC na COPEL (ex: 113577680)
    contract_number: Optional[str] = None
    address: str
    city: Optional[str] = None
    state: str = "PR"
    holder_name: Optional[str] = None
    holder_document: Optional[str] = None  # CPF/CNPJ
    is_generator: bool = False  # Se é UC geradora
    compensation_percentage: float = 100.0  # % de compensação que recebe (0-100)
    tariff_group: str = "B"  # A ou B
    tariff_modality: Optional[str] = None  # Convencional, Horária, etc
    contracted_demand_kw: Optional[float] = None  # Demanda contratada (Grupo A)
    generator_uc_ids: Optional[List[str]] = None  # IDs das UCs geradoras que abastecem esta UC

class ConsumerUnitCreate(ConsumerUnitBase):
    pass

class ConsumerUnit(ConsumerUnitBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

class GenerationDataBase(BaseModel):
    plant_id: str
    date: str
    generation_kwh: float
    source: str = "manual"

class GenerationDataCreate(GenerationDataBase):
    pass

class GenerationData(GenerationDataBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InvoiceDataBase(BaseModel):
    consumer_unit_id: str
    plant_id: str
    reference_month: str  # MM/YYYY
    billing_cycle_start: str
    billing_cycle_end: str
    due_date: Optional[str] = None
    
    # Valores financeiros
    amount_total_brl: float = 0  # Total a pagar
    amount_saved_brl: float = 0  # Economizado
    
    # Dados de energia - Fora Ponta
    energy_registered_fp_kwh: float = 0
    energy_tariff_fp_brl: float = 0
    energy_billed_fp_kwh: float = 0
    energy_injected_fp_kwh: float = 0
    energy_compensated_fp_kwh: float = 0
    credits_accumulated_fp_kwh: float = 0
    tariff_te_fp_brl: float = 0
    
    # Dados de energia - Ponta (Grupo A)
    energy_registered_p_kwh: float = 0
    energy_tariff_p_brl: float = 0
    energy_billed_p_kwh: float = 0
    energy_injected_p_kwh: float = 0
    energy_compensated_p_kwh: float = 0
    credits_accumulated_p_kwh: float = 0
    tariff_te_p_brl: float = 0
    
    # Demanda (Grupo A)
    demand_registered_kw: float = 0
    demand_contracted_kw: float = 0
    demand_billed_kw: float = 0
    
    # Créditos
    credits_balance_p_kwh: float = 0
    credits_balance_fp_kwh: float = 0
    
    # Iluminação pública
    public_lighting_brl: float = 0
    
    # Tributos
    icms_brl: float = 0
    pis_cofins_brl: float = 0
    
    # Metadados
    tariff_group: str = "B"  # A ou B
    is_generator: bool = False
    pdf_file_path: Optional[str] = None
    source: str = "manual"  # manual, copel_api, upload

class InvoiceDataCreate(InvoiceDataBase):
    pass

class InvoiceData(InvoiceDataBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InverterCredentialBase(BaseModel):
    plant_id: str
    brand: str
    username: str
    password: str  # Will be encrypted before storage

class InverterCredentialCreate(InverterCredentialBase):
    pass

class InverterCredential(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plant_id: str
    brand: str
    username: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_sync: Optional[datetime] = None
    is_active: bool = True

class CopelCredentialBase(BaseModel):
    consumer_unit_id: str
    cpf: str
    password: str

class CopelCredentialCreate(CopelCredentialBase):
    pass

class CopelCredential(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    consumer_unit_id: str
    cpf: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_sync: Optional[datetime] = None
    is_active: bool = True

# Lista de Distribuição de Créditos
class CreditDistributionUC(BaseModel):
    consumer_unit_id: str
    uc_number: str
    address: str
    classification: str  # A4-Comercial, B1-Residencial, B3-Comercial
    percentage: float  # Porcentagem de compensação
    is_generator: bool = False

class CreditDistributionListBase(BaseModel):
    plant_id: str
    name: str  # Ex: "Vigência 12/2025 - Baseada em Lista de Porcentagem"
    effective_date: str  # Data de vigência MM/YYYY
    distribution_type: str = "percentage"  # percentage, kwh
    units: List[CreditDistributionUC] = []

class CreditDistributionListCreate(CreditDistributionListBase):
    pass

class CreditDistributionList(CreditDistributionListBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

# Relatórios Mensais
class MonthlyReportBase(BaseModel):
    plant_id: str
    reference_month: str  # MM/YYYY
    year: int
    month: int
    performance_percentage: float = 0  # Desempenho %
    total_generation_kwh: float = 0
    prognosis_kwh: float = 0
    status: str = "pending"  # pending, generated, sent
    pdf_url: Optional[str] = None
    notes: Optional[str] = None

class MonthlyReportCreate(MonthlyReportBase):
    pass

class MonthlyReport(MonthlyReportBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    generated_at: Optional[datetime] = None

# Timeline de Atividades
class ActivityLogBase(BaseModel):
    plant_id: str
    action: str  # edited_report, changed_prognosis, uploaded_invoice, etc
    description: str
    user_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class ActivityLog(ActivityLogBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(user_id: str, email: str) -> str:
    payload = {
        'sub': user_id,
        'email': email,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.now(timezone.utc),
        'type': 'access'
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {
        'sub': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_EXPIRATION_DAYS),
        'iat': datetime.now(timezone.utc),
        'type': 'refresh'
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get('type') != 'access':
            raise HTTPException(status_code=401, detail="Token inválido")
        user = await db.users.find_one({'id': payload['sub']}, {'_id': 0, 'password_hash': 0})
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({'email': user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    user = User(email=user_data.email, name=user_data.name, role=user_data.role)
    doc = user.model_dump()
    doc['password_hash'] = hash_password(user_data.password)
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    
    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role}
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({'email': credentials.email}, {'_id': 0})
    if not user or not verify_password(credentials.password, user.get('password_hash', '')):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    
    access_token = create_access_token(user['id'], user['email'])
    refresh_token = create_refresh_token(user['id'])
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={'id': user['id'], 'email': user['email'], 'name': user['name'], 'role': user['role']}
    )

@api_router.post("/auth/refresh")
async def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get('type') != 'refresh':
            raise HTTPException(status_code=401, detail="Token inválido")
        
        user = await db.users.find_one({'id': payload['sub']}, {'_id': 0, 'password_hash': 0})
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        
        new_access_token = create_access_token(user['id'], user['email'])
        new_refresh_token = create_refresh_token(user['id'])
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            user={'id': user['id'], 'email': user['email'], 'name': user['name'], 'role': user['role']}
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@api_router.post("/auth/change-password")
async def change_password(request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    # Get user with password hash
    user = await db.users.find_one({'id': current_user['id']}, {'_id': 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Verify current password
    if not verify_password(request.current_password, user.get('password_hash', '')):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    
    # Update password
    new_hash = hash_password(request.new_password)
    await db.users.update_one(
        {'id': current_user['id']},
        {'$set': {'password_hash': new_hash}}
    )
    
    return {"message": "Senha alterada com sucesso"}

# Seed initial users on startup
async def seed_users():
    """Create initial users if they don't exist"""
    initial_users = [
        {"email": "projetos.onsolucoes@gmail.com", "name": "João", "role": "admin"},
        {"email": "comercial.onsolucoes@gmail.com", "name": "Mateus", "role": "user"},
        {"email": "gerencia.onsolucoes@gmail.com", "name": "Roberto", "role": "user"},
        {"email": "fabioonsolucoes@gmail.com", "name": "Fabio", "role": "user"},
    ]
    
    default_password = "on123456"
    
    for user_data in initial_users:
        existing = await db.users.find_one({'email': user_data['email']})
        if not existing:
            user = User(**user_data)
            doc = user.model_dump()
            doc['password_hash'] = hash_password(default_password)
            doc['created_at'] = doc['created_at'].isoformat()
            await db.users.insert_one(doc)
            logger.info(f"Created user: {user_data['email']}")

async def seed_irradiance_cities():
    """Seed irradiance cities data if collection is empty"""
    import json
    count = await db.irradiance_cities.count_documents({})
    if count > 0:
        logger.info(f"Irradiance cities already populated: {count} cities")
        return
    
    # Load from JSON file
    json_path = ROOT_DIR / 'data' / 'irradiance_cities.json'
    if not json_path.exists():
        logger.warning(f"Irradiance cities JSON not found at {json_path}")
        return
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            cities = json.load(f)
        
        if cities:
            # Insert in batches
            batch_size = 500
            for i in range(0, len(cities), batch_size):
                batch = cities[i:i+batch_size]
                await db.irradiance_cities.insert_many(batch)
            logger.info(f"Seeded {len(cities)} irradiance cities")
    except Exception as e:
        logger.error(f"Failed to seed irradiance cities: {e}")

@app.on_event("startup")
async def startup_event():
    await seed_users()
    await seed_irradiance_cities()
    
    # Start Playwright installation in background (non-blocking)
    import asyncio
    import subprocess
    
    async def install_playwright_background():
        """Install Playwright browsers in background without blocking startup"""
        await asyncio.sleep(2)  # Let the server start first
        try:
            env = os.environ.copy()
            env['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'
            # Install browser in background
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ['playwright', 'install', 'chromium'],
                    capture_output=True, text=True, timeout=180, env=env
                )
            )
            logger.info(f"Playwright install chromium: exit={result.returncode}")
            if result.stderr:
                logger.info(f"Playwright stderr: {result.stderr[:300]}")
            # Install system dependencies
            result2 = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ['playwright', 'install-deps', 'chromium'],
                    capture_output=True, text=True, timeout=180, env=env
                )
            )
            logger.info(f"Playwright install-deps: exit={result2.returncode}")
            logger.info("Playwright browsers verified/installed")
        except Exception as e:
            logger.warning(f"Playwright browser install issue: {e}")
    
    # Fire and forget - don't await this
    asyncio.create_task(install_playwright_background())
    
    # Start scheduled jobs
    try:
        from services.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        logger.warning(f"Scheduler start failed: {e}")

# ==================== CLIENTS ROUTES ====================

@api_router.get("/clients", response_model=List[Client])
async def list_clients(current_user: dict = Depends(get_current_user)):
    clients = await db.clients.find({'is_active': True}, {'_id': 0}).to_list(1000)
    for c in clients:
        if isinstance(c.get('created_at'), str):
            c['created_at'] = datetime.fromisoformat(c['created_at'])
    return clients

@api_router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: str, current_user: dict = Depends(get_current_user)):
    client = await db.clients.find_one({'id': client_id, 'is_active': True}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    if isinstance(client.get('created_at'), str):
        client['created_at'] = datetime.fromisoformat(client['created_at'])
    return client

@api_router.post("/clients", response_model=Client)
async def create_client(client_data: ClientCreate, current_user: dict = Depends(get_current_user)):
    client = Client(**client_data.model_dump())
    doc = client.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.clients.insert_one(doc)
    return client

@api_router.put("/clients/{client_id}", response_model=Client)
async def update_client(client_id: str, client_data: ClientCreate, current_user: dict = Depends(get_current_user)):
    result = await db.clients.update_one(
        {'id': client_id, 'is_active': True},
        {'$set': client_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return await get_client(client_id, current_user)

@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.clients.update_one({'id': client_id}, {'$set': {'is_active': False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"message": "Cliente removido com sucesso"}

# ==================== LOGO UPLOAD ====================

LOGO_UPLOAD_DIR = "/tmp/logos"
os.makedirs(LOGO_UPLOAD_DIR, exist_ok=True)

# Initialize Cloudinary
from services.cloudinary_service import init_cloudinary, upload_logo as cloudinary_upload, get_logo_thumbnail_url
init_cloudinary()

async def auto_calculate_prognosis(plant_id: str, city: str, capacity_kwp: float):
    """Auto-calculate and save monthly/annual prognosis based on city irradiance."""
    if not city or capacity_kwp <= 0:
        return
    import re as re_mod
    city_doc = await db.irradiance_cities.find_one(
        {'city': {'$regex': f'^{re_mod.escape(city)}', '$options': 'i'}},
        {'_id': 0, 'irradiance': 1, 'city': 1}
    )
    if not city_doc:
        return
    irr = city_doc.get('irradiance', {})
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    months_key = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
    total = sum(capacity_kwp * month_days[i] * ((irr.get(mk, 0) / 1000) - 0.1) * 0.75 for i, mk in enumerate(months_key))
    avg = total / 12
    await db.plants.update_one({'id': plant_id}, {'$set': {
        'monthly_prognosis_kwh': round(avg, 2),
        'annual_prognosis_kwh': round(total, 2),
        'city': city_doc['city'],  # Use correct full name from DB
    }})

@api_router.post("/upload/logo/{entity_type}/{entity_id}")
async def upload_logo(
    entity_type: str,
    entity_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload logo to Cloudinary in USINAS folder"""
    if entity_type not in ["client", "plant"]:
        raise HTTPException(status_code=400, detail="Tipo invalido. Use 'client' ou 'plant'")
    
    allowed_types = [".png", ".jpg", ".jpeg", ".webp", ".svg"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Tipo de arquivo nao suportado. Use: {', '.join(allowed_types)}")
    
    collection = db.clients if entity_type == "client" else db.plants
    entity = await collection.find_one({'id': entity_id, 'is_active': True})
    if not entity:
        raise HTTPException(status_code=404, detail="Entidade nao encontrada")
    
    # Read file bytes
    file_bytes = await file.read()
    
    # Upload to Cloudinary
    try:
        result = cloudinary_upload(file_bytes, f"{entity_type}_{entity_id}", entity_type)
        logo_url = result['secure_url']
        logo_public_id = result['public_id']
    except Exception as e:
        logger.error(f"Cloudinary upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar para Cloudinary: {str(e)}")
    
    # Update entity with Cloudinary URL
    await collection.update_one(
        {'id': entity_id},
        {'$set': {
            'logo_url': logo_url,
            'logo_public_id': logo_public_id,
        }}
    )
    
    return {
        "success": True,
        "logo_url": logo_url,
        "logo_public_id": logo_public_id,
        "thumbnail_url": get_logo_thumbnail_url(logo_public_id),
    }

@api_router.get("/logos/{filename}")
async def get_logo(filename: str):
    """Serve logo file (legacy - for old logos saved on disk)"""
    from fastapi.responses import FileResponse
    filepath = os.path.join(LOGO_UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Logo nao encontrado")
    return FileResponse(filepath)

# ==================== PLANTS ROUTES ====================

@api_router.get("/plants", response_model=List[Plant])
async def list_plants(client_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {'is_active': True}
    if client_id:
        query['client_id'] = client_id
    plants = await db.plants.find(query, {'_id': 0}).to_list(1000)
    for p in plants:
        if isinstance(p.get('created_at'), str):
            p['created_at'] = datetime.fromisoformat(p['created_at'])
    return plants

@api_router.get("/plants/{plant_id}", response_model=Plant)
async def get_plant(plant_id: str, current_user: dict = Depends(get_current_user)):
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True}, {'_id': 0})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    if isinstance(plant.get('created_at'), str):
        plant['created_at'] = datetime.fromisoformat(plant['created_at'])
    return plant

@api_router.post("/plants", response_model=Plant)
async def create_plant(plant_data: PlantCreate, current_user: dict = Depends(get_current_user)):
    # Verify client exists
    client = await db.clients.find_one({'id': plant_data.client_id, 'is_active': True})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    plant = Plant(**plant_data.model_dump())
    doc = plant.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.plants.insert_one(doc)
    return plant

@api_router.put("/plants/{plant_id}", response_model=Plant)
async def update_plant(plant_id: str, plant_data: PlantCreate, current_user: dict = Depends(get_current_user)):
    result = await db.plants.update_one(
        {'id': plant_id, 'is_active': True},
        {'$set': plant_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    
    # Auto-calculate prognosis if city changed and no manual prognosis set
    data = plant_data.model_dump()
    city = data.get('city', '')
    kwp = data.get('capacity_kwp', 0)
    if city and kwp > 0:
        await auto_calculate_prognosis(plant_id, city, kwp)
    
    return await get_plant(plant_id, current_user)

@api_router.delete("/plants/{plant_id}")
async def delete_plant(plant_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.plants.update_one({'id': plant_id}, {'$set': {'is_active': False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    return {"message": "Usina removida com sucesso"}

# ==================== CONSUMER UNITS ROUTES ====================

@api_router.get("/consumer-units")
async def list_consumer_units(plant_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {'is_active': True}
    if plant_id:
        query['plant_id'] = plant_id
    units = await db.consumer_units.find(query, {'_id': 0}).to_list(1000)
    
    # Normalize units for backwards compatibility
    result = []
    for u in units:
        if isinstance(u.get('created_at'), str):
            u['created_at'] = datetime.fromisoformat(u['created_at'])
        
        # Migrate old format - use contract_number as uc_number if missing
        if not u.get('uc_number') and u.get('contract_number'):
            u['uc_number'] = u['contract_number']
            # Update in database
            await db.consumer_units.update_one(
                {'id': u['id']},
                {'$set': {'uc_number': u['contract_number']}}
            )
        elif not u.get('uc_number'):
            u['uc_number'] = u.get('id', '')[:9]  # Fallback
        
        # Ensure all new fields exist with defaults
        u.setdefault('city', None)
        u.setdefault('state', 'PR')
        u.setdefault('holder_document', None)
        u.setdefault('compensation_percentage', 100.0)
        u.setdefault('tariff_group', 'B')
        u.setdefault('tariff_modality', None)
        u.setdefault('contracted_demand_kw', None)
        u.setdefault('generator_uc_ids', None)
        
        result.append(u)
    
    return result

@api_router.get("/consumer-units/{unit_id}", response_model=ConsumerUnit)
async def get_consumer_unit(unit_id: str, current_user: dict = Depends(get_current_user)):
    unit = await db.consumer_units.find_one({'id': unit_id, 'is_active': True}, {'_id': 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unidade consumidora não encontrada")
    if isinstance(unit.get('created_at'), str):
        unit['created_at'] = datetime.fromisoformat(unit['created_at'])
    return unit

@api_router.post("/consumer-units", response_model=ConsumerUnit)
async def create_consumer_unit(unit_data: ConsumerUnitCreate, current_user: dict = Depends(get_current_user)):
    # Verify plant exists
    plant = await db.plants.find_one({'id': unit_data.plant_id, 'is_active': True})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    
    unit = ConsumerUnit(**unit_data.model_dump())
    doc = unit.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.consumer_units.insert_one(doc)
    return unit

@api_router.put("/consumer-units/{unit_id}", response_model=ConsumerUnit)
async def update_consumer_unit(unit_id: str, unit_data: ConsumerUnitCreate, current_user: dict = Depends(get_current_user)):
    result = await db.consumer_units.update_one(
        {'id': unit_id, 'is_active': True},
        {'$set': unit_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Unidade consumidora não encontrada")
    return await get_consumer_unit(unit_id, current_user)

@api_router.delete("/consumer-units/{unit_id}")
async def delete_consumer_unit(unit_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.consumer_units.update_one({'id': unit_id}, {'$set': {'is_active': False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Unidade consumidora não encontrada")
    return {"message": "Unidade consumidora removida com sucesso"}

# ==================== GENERATION DATA ROUTES ====================

@api_router.get("/generation-data", response_model=List[GenerationData])
async def list_generation_data(
    plant_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {'plant_id': plant_id}
    if start_date:
        query['date'] = {'$gte': start_date}
    if end_date:
        if 'date' in query:
            query['date']['$lte'] = end_date
        else:
            query['date'] = {'$lte': end_date}
    
    data = await db.generation_data.find(query, {'_id': 0}).sort('date', 1).to_list(10000)
    for d in data:
        if isinstance(d.get('created_at'), str):
            d['created_at'] = datetime.fromisoformat(d['created_at'])
    return data

@api_router.post("/generation-data", response_model=GenerationData)
async def create_generation_data(gen_data: GenerationDataCreate, current_user: dict = Depends(get_current_user)):
    # Verify plant exists
    plant = await db.plants.find_one({'id': gen_data.plant_id, 'is_active': True})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    
    # Check if data for this date already exists
    existing = await db.generation_data.find_one({'plant_id': gen_data.plant_id, 'date': gen_data.date})
    if existing:
        # Update existing
        await db.generation_data.update_one(
            {'plant_id': gen_data.plant_id, 'date': gen_data.date},
            {'$set': {'generation_kwh': gen_data.generation_kwh, 'source': gen_data.source}}
        )
        updated = await db.generation_data.find_one({'plant_id': gen_data.plant_id, 'date': gen_data.date}, {'_id': 0})
        if isinstance(updated.get('created_at'), str):
            updated['created_at'] = datetime.fromisoformat(updated['created_at'])
        return updated
    
    data = GenerationData(**gen_data.model_dump())
    doc = data.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.generation_data.insert_one(doc)
    return data

@api_router.post("/generation-data/upload/{plant_id}")
async def upload_generation_data(
    plant_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    # Verify plant exists
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    
    # Read file
    content = await file.read()
    
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Formato de arquivo não suportado. Use CSV ou Excel.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler arquivo: {str(e)}")
    
    # Normalize column names
    df.columns = df.columns.str.lower().str.strip()
    
    # Find date and generation columns
    date_col = None
    gen_col = None
    
    for col in df.columns:
        if 'data' in col or 'date' in col or 'dia' in col:
            date_col = col
        if 'gera' in col or 'kwh' in col or 'energia' in col or 'produc' in col:
            gen_col = col
    
    if not date_col or not gen_col:
        raise HTTPException(status_code=400, detail="Colunas de data e geração não encontradas. Use 'data' e 'geracao_kwh'.")
    
    # Process and insert data
    records_inserted = 0
    records_updated = 0
    
    for _, row in df.iterrows():
        try:
            date_val = row[date_col]
            if isinstance(date_val, str):
                # Try different date formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                    try:
                        date_val = datetime.strptime(date_val, fmt).strftime('%Y-%m-%d')
                        break
                    except:
                        continue
            else:
                date_val = pd.to_datetime(date_val).strftime('%Y-%m-%d')
            
            gen_val = float(row[gen_col])
            
            existing = await db.generation_data.find_one({'plant_id': plant_id, 'date': date_val})
            if existing:
                await db.generation_data.update_one(
                    {'plant_id': plant_id, 'date': date_val},
                    {'$set': {'generation_kwh': gen_val, 'source': 'upload'}}
                )
                records_updated += 1
            else:
                data = GenerationData(plant_id=plant_id, date=date_val, generation_kwh=gen_val, source='upload')
                doc = data.model_dump()
                doc['created_at'] = doc['created_at'].isoformat()
                await db.generation_data.insert_one(doc)
                records_inserted += 1
        except Exception as e:
            logger.warning(f"Error processing row: {e}")
            continue
    
    return {
        "message": "Upload concluído",
        "records_inserted": records_inserted,
        "records_updated": records_updated,
        "total_processed": records_inserted + records_updated
    }

# ==================== INVOICE DATA ROUTES ====================

@api_router.get("/invoices", response_model=List[InvoiceData])
async def list_invoices(
    plant_id: Optional[str] = None,
    consumer_unit_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if plant_id:
        query['plant_id'] = plant_id
    if consumer_unit_id:
        query['consumer_unit_id'] = consumer_unit_id
    
    invoices = await db.invoices.find(query, {'_id': 0}).sort('billing_cycle_end', -1).to_list(1000)
    for i in invoices:
        if isinstance(i.get('created_at'), str):
            i['created_at'] = datetime.fromisoformat(i['created_at'])
    return invoices

@api_router.post("/invoices", response_model=InvoiceData)
async def create_invoice(invoice_data: InvoiceDataCreate, current_user: dict = Depends(get_current_user)):
    invoice = InvoiceData(**invoice_data.model_dump())
    doc = invoice.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.invoices.insert_one(doc)
    return invoice

@api_router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    invoice = await db.invoices.find_one({'id': invoice_id}, {'_id': 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Fatura não encontrada")
    if isinstance(invoice.get('created_at'), str):
        invoice['created_at'] = datetime.fromisoformat(invoice['created_at'])
    return invoice

@api_router.put("/invoices/{invoice_id}")
async def update_invoice(invoice_id: str, invoice_data: InvoiceDataCreate, current_user: dict = Depends(get_current_user)):
    result = await db.invoices.update_one(
        {'id': invoice_id},
        {'$set': invoice_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Fatura não encontrada")
    return await get_invoice(invoice_id, current_user)

@api_router.delete("/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.invoices.delete_one({'id': invoice_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Fatura não encontrada")
    return {"message": "Fatura removida com sucesso"}

# ==================== INVOICE PDF UPLOAD ====================

from services.pdf_parser_service import parse_copel_invoice
import shutil

UPLOAD_DIR = "/tmp/invoice_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@api_router.post("/invoices/upload-pdf-auto")
async def upload_invoice_pdf_auto(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a COPEL invoice PDF and auto-detect the consumer unit by UC number.
    The system will automatically find the matching UC.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos")
    
    # Save file temporarily
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"fatura_auto_{timestamp}.pdf"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    try:
        with open(filepath, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")
    
    # Parse PDF
    try:
        parsed_data = parse_copel_invoice(filepath)
    except Exception as e:
        logger.error(f"Error parsing PDF: {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao processar PDF: {str(e)}",
            "filepath": filepath
        }
    
    if not parsed_data.get('success'):
        return {
            "success": False,
            "error": parsed_data.get('error', 'Erro desconhecido'),
            "filepath": filepath
        }
    
    # Extract UC number from PDF
    uc_number = parsed_data.get('uc_number')
    if not uc_number:
        return {
            "success": False,
            "error": "Não foi possível identificar o número da UC na fatura. Verifique se o PDF é válido.",
            "filepath": filepath,
            "parsed_data": parsed_data
        }
    
    # Find the consumer unit by UC number
    unit = await db.consumer_units.find_one({'uc_number': uc_number, 'is_active': True}, {'_id': 0})
    
    if not unit:
        # UC not found - return data so user can add it
        return {
            "success": True,
            "uc_found": False,
            "message": f"UC {uc_number} não encontrada no sistema. Cadastre-a primeiro ou verifique o número.",
            "filepath": filepath,
            "uc_number": uc_number,
            "parsed_data": {
                "uc_number": uc_number,
                "holder_name": parsed_data.get('holder_name'),
                "holder_document": parsed_data.get('holder_document'),
                "address": parsed_data.get('address'),
                "city": parsed_data.get('city'),
                "classification": parsed_data.get('classification'),
                "tariff_group": parsed_data.get('tariff_group'),
                "is_generator": parsed_data.get('is_generator', False),
                "reference_month": parsed_data.get('reference_month'),
                "amount_total_brl": parsed_data.get('amount_total_brl', 0),
            }
        }
    
    # Get plant info
    plant = await db.plants.find_one({'id': unit.get('plant_id'), 'is_active': True}, {'_id': 0})
    
    # Return full parsed data
    return {
        "success": True,
        "uc_found": True,
        "message": f"Fatura da UC {uc_number} processada com sucesso!",
        "filepath": filepath,
        "consumer_unit": {
            "id": unit.get('id'),
            "uc_number": unit.get('uc_number'),
            "holder_name": unit.get('holder_name'),
            "address": unit.get('address'),
            "plant_id": unit.get('plant_id'),
            "plant_name": plant.get('name') if plant else None
        },
        "parsed_data": {
            "consumer_unit_id": unit.get('id'),
            "plant_id": unit.get('plant_id'),
            "uc_number": uc_number,
            "holder_name": parsed_data.get('holder_name'),
            "holder_document": parsed_data.get('holder_document'),
            "classification": parsed_data.get('classification'),
            "tariff_group": parsed_data.get('tariff_group'),
            "is_generator": parsed_data.get('is_generator', False),
            "tariff_flag": parsed_data.get('tariff_flag'),
            "reference_month": parsed_data.get('reference_month'),
            "billing_cycle_start": parsed_data.get('billing_cycle_start'),
            "billing_cycle_end": parsed_data.get('billing_cycle_end'),
            "due_date": parsed_data.get('due_date'),
            "amount_total_brl": parsed_data.get('amount_total_brl', 0),
            "amount_saved_brl": parsed_data.get('amount_saved_brl', 0),
            "public_lighting_brl": parsed_data.get('public_lighting_brl', 0),
            "icms_brl": parsed_data.get('icms_brl', 0),
            "pis_brl": parsed_data.get('pis_brl', 0),
            "cofins_brl": parsed_data.get('cofins_brl', 0),
            # Energy data - Fora Ponta
            "energy_registered_fp_kwh": parsed_data.get('energy_registered_fp_kwh', 0),
            "energy_injected_fp_kwh": parsed_data.get('energy_injected_fp_kwh', 0),
            "energy_compensated_fp_kwh": parsed_data.get('energy_compensated_fp_kwh', 0),
            "energy_billed_fp_kwh": parsed_data.get('energy_billed_fp_kwh', 0),
            "credits_balance_fp_kwh": parsed_data.get('credits_balance_fp_kwh', 0),
            "credits_accumulated_fp_kwh": parsed_data.get('credits_accumulated_fp_kwh', 0),
            # Energy data - Ponta (Group A only)
            "energy_registered_p_kwh": parsed_data.get('energy_registered_p_kwh', 0),
            "energy_injected_p_kwh": parsed_data.get('energy_injected_p_kwh', 0),
            "energy_compensated_p_kwh": parsed_data.get('energy_compensated_p_kwh', 0),
            "energy_billed_p_kwh": parsed_data.get('energy_billed_p_kwh', 0),
            "credits_balance_p_kwh": parsed_data.get('credits_balance_p_kwh', 0),
            "credits_accumulated_p_kwh": parsed_data.get('credits_accumulated_p_kwh', 0),
            # Demand data (Group A only)
            "demand_contracted_kw": parsed_data.get('demand_contracted_kw', 0),
            "demand_measured_kw": parsed_data.get('demand_measured_kw', 0),
            "demand_injected_kw": parsed_data.get('demand_injected_kw', 0),
            # Tariffs
            "tariff_values": parsed_data.get('tariff_values', {}),
        }
    }

@api_router.post("/invoices/upload-pdf/{consumer_unit_id}")
async def upload_invoice_pdf(
    consumer_unit_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a COPEL invoice PDF and extract data automatically
    """
    # Verify consumer unit exists
    unit = await db.consumer_units.find_one({'id': consumer_unit_id, 'is_active': True}, {'_id': 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unidade consumidora não encontrada")
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos")
    
    # Save file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"fatura_{consumer_unit_id}_{timestamp}.pdf"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    try:
        with open(filepath, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")
    
    # Parse PDF
    try:
        parsed_data = parse_copel_invoice(filepath)
    except Exception as e:
        logger.error(f"Error parsing PDF: {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao processar PDF: {str(e)}",
            "filepath": filepath
        }
    
    if not parsed_data.get('success'):
        return {
            "success": False,
            "error": parsed_data.get('error', 'Erro desconhecido'),
            "filepath": filepath
        }
    
    # Return parsed data for user to confirm/edit before saving
    return {
        "success": True,
        "message": "PDF processado com sucesso. Revise os dados antes de salvar.",
        "filepath": filepath,
        "parsed_data": {
            "consumer_unit_id": consumer_unit_id,
            "plant_id": unit.get('plant_id'),
            "uc_number": parsed_data.get('uc_number'),
            "holder_name": parsed_data.get('holder_name'),
            "reference_month": parsed_data.get('reference_month'),
            "billing_cycle_start": parsed_data.get('billing_cycle_start'),
            "billing_cycle_end": parsed_data.get('billing_cycle_end'),
            "due_date": parsed_data.get('due_date'),
            "amount_total_brl": parsed_data.get('amount_total_brl', 0),
            "amount_saved_brl": parsed_data.get('amount_saved_brl', 0),
            "energy_registered_fp_kwh": parsed_data.get('energy_registered_fp_kwh', 0),
            "energy_tariff_fp_brl": parsed_data.get('energy_tariff_fp_brl', 0),
            "energy_billed_fp_kwh": parsed_data.get('energy_billed_fp_kwh', 0),
            "energy_injected_fp_kwh": parsed_data.get('energy_injected_fp_kwh', 0),
            "energy_compensated_fp_kwh": parsed_data.get('energy_compensated_fp_kwh', 0),
            "credits_accumulated_fp_kwh": parsed_data.get('credits_accumulated_fp_kwh', 0),
            "energy_registered_p_kwh": parsed_data.get('energy_registered_p_kwh', 0),
            "energy_injected_p_kwh": parsed_data.get('energy_injected_p_kwh', 0),
            "energy_compensated_p_kwh": parsed_data.get('energy_compensated_p_kwh', 0),
            "credits_accumulated_p_kwh": parsed_data.get('credits_accumulated_p_kwh', 0),
            "demand_registered_kw": parsed_data.get('demand_registered_kw', 0),
            "public_lighting_brl": parsed_data.get('public_lighting_brl', 0),
            "icms_brl": parsed_data.get('icms_brl', 0),
            "tariff_group": parsed_data.get('tariff_group', 'B'),
            "is_generator": parsed_data.get('is_generator', False),
            "credits_balance_p_kwh": parsed_data.get('credits_balance_p_kwh', 0),
            "credits_balance_fp_kwh": parsed_data.get('credits_balance_fp_kwh', 0),
            "pdf_file_path": filepath,
            "source": "upload"
        }
    }

@api_router.post("/invoices/save-from-upload")
async def save_invoice_from_upload(invoice_data: dict, current_user: dict = Depends(get_current_user)):
    """
    Save invoice data after user review/edit from PDF upload
    """
    # Verify consumer unit exists
    consumer_unit_id = invoice_data.get('consumer_unit_id')
    if not consumer_unit_id:
        raise HTTPException(status_code=400, detail="consumer_unit_id é obrigatório")
    
    unit = await db.consumer_units.find_one({'id': consumer_unit_id, 'is_active': True})
    if not unit:
        raise HTTPException(status_code=404, detail="Unidade consumidora não encontrada")
    
    # Check for duplicate - same UC + same reference month
    ref_month = invoice_data.get('reference_month', '')
    if ref_month:
        existing = await db.invoices.find_one({
            'consumer_unit_id': consumer_unit_id,
            'reference_month': ref_month
        })
        if existing:
            raise HTTPException(status_code=409, detail=f"Fatura ja existe para UC {unit.get('uc_number','')} ref {ref_month}")
    
    # Create invoice record
    invoice = InvoiceData(
        consumer_unit_id=consumer_unit_id,
        plant_id=invoice_data.get('plant_id', unit.get('plant_id')),
        reference_month=invoice_data.get('reference_month', ''),
        billing_cycle_start=invoice_data.get('billing_cycle_start', ''),
        billing_cycle_end=invoice_data.get('billing_cycle_end', ''),
        due_date=invoice_data.get('due_date'),
        amount_total_brl=invoice_data.get('amount_total_brl', 0),
        amount_saved_brl=invoice_data.get('amount_saved_brl', 0),
        energy_registered_fp_kwh=invoice_data.get('energy_registered_fp_kwh', 0),
        energy_tariff_fp_brl=invoice_data.get('energy_tariff_fp_brl', 0),
        energy_billed_fp_kwh=invoice_data.get('energy_billed_fp_kwh', 0),
        energy_injected_fp_kwh=invoice_data.get('energy_injected_fp_kwh', 0),
        energy_compensated_fp_kwh=invoice_data.get('energy_compensated_fp_kwh', 0),
        credits_accumulated_fp_kwh=invoice_data.get('credits_accumulated_fp_kwh', 0),
        energy_registered_p_kwh=invoice_data.get('energy_registered_p_kwh', 0),
        energy_injected_p_kwh=invoice_data.get('energy_injected_p_kwh', 0),
        energy_compensated_p_kwh=invoice_data.get('energy_compensated_p_kwh', 0),
        credits_accumulated_p_kwh=invoice_data.get('credits_accumulated_p_kwh', 0),
        demand_registered_kw=invoice_data.get('demand_registered_kw', 0),
        public_lighting_brl=invoice_data.get('public_lighting_brl', 0),
        icms_brl=invoice_data.get('icms_brl', 0),
        tariff_group=invoice_data.get('tariff_group', 'B'),
        is_generator=invoice_data.get('is_generator', False),
        credits_balance_p_kwh=invoice_data.get('credits_balance_p_kwh', 0),
        credits_balance_fp_kwh=invoice_data.get('credits_balance_fp_kwh', 0),
        pdf_file_path=invoice_data.get('pdf_file_path'),
        source=invoice_data.get('source', 'upload')
    )
    
    doc = invoice.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['uc_number'] = unit.get('uc_number', '')
    await db.invoices.insert_one(doc)
    
    return {
        "success": True,
        "message": f"Fatura salva: UC {unit.get('uc_number','')} ref {ref_month}",
        "invoice_id": invoice.id
    }

# ==================== DASHBOARD STATS ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    # Count active plants
    total_plants = await db.plants.count_documents({'is_active': True})
    
    # Count active clients
    total_clients = await db.clients.count_documents({'is_active': True})
    
    # Get total capacity
    plants = await db.plants.find({'is_active': True}, {'_id': 0, 'capacity_kwp': 1}).to_list(1000)
    total_capacity_kwp = sum(p.get('capacity_kwp', 0) for p in plants)
    
    # Get current month generation
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1).strftime('%Y-%m-%d')
    month_end = now.strftime('%Y-%m-%d')
    
    gen_data = await db.generation_data.find({
        'date': {'$gte': month_start, '$lte': month_end}
    }, {'_id': 0, 'generation_kwh': 1}).to_list(100000)
    
    total_generation_kwh = sum(d.get('generation_kwh', 0) for d in gen_data)
    
    # Get total saved this month from invoices
    invoices = await db.invoices.find({
        'billing_cycle_end': {'$gte': month_start}
    }, {'_id': 0, 'amount_saved_brl': 1, 'amount_billed_brl': 1}).to_list(10000)
    
    total_saved_brl = sum(i.get('amount_saved_brl', 0) for i in invoices)
    total_billed_brl = sum(i.get('amount_billed_brl', 0) for i in invoices)
    
    # Calculate CO2 avoided (0.5 kg CO2 per kWh is average for Brazil)
    co2_avoided_kg = total_generation_kwh * 0.5
    
    # Trees equivalent (1 tree absorbs ~22 kg CO2/year, so per month ~1.83 kg)
    trees_equivalent = co2_avoided_kg / 1.83
    
    return {
        "total_plants": total_plants,
        "total_clients": total_clients,
        "total_capacity_kwp": round(total_capacity_kwp, 2),
        "total_generation_kwh": round(total_generation_kwh, 2),
        "total_saved_brl": round(total_saved_brl, 2),
        "total_billed_brl": round(total_billed_brl, 2),
        "co2_avoided_kg": round(co2_avoided_kg, 2),
        "trees_equivalent": round(trees_equivalent, 0),
        "month": now.strftime('%m/%Y')
    }

@api_router.get("/dashboard/plants-summary")
async def get_plants_summary(current_user: dict = Depends(get_current_user)):
    plants = await db.plants.find({'is_active': True}, {'_id': 0}).to_list(1000)
    
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1).strftime('%Y-%m-%d')
    
    total_capacity_mwp = 0
    total_gen_all = 0
    summaries = []
    for plant in plants:
        # Get installation date
        install_date_str = plant.get('installation_date', '')
        install_date = None
        if install_date_str:
            try:
                install_date = datetime.strptime(install_date_str[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except:
                pass
        
        # Get generation for this month (only after installation)
        query_start = month_start
        if install_date and install_date.strftime('%Y-%m-%d') > month_start:
            query_start = install_date.strftime('%Y-%m-%d')
        
        gen_data = await db.generation_data.find({
            'plant_id': plant['id'],
            'date': {'$gte': query_start}
        }, {'_id': 0, 'generation_kwh': 1, 'date': 1}).to_list(100)
        
        total_gen = sum(d.get('generation_kwh', 0) for d in gen_data)
        prognosis = plant.get('monthly_prognosis_kwh') or 0
        
        # Calculate effective days in this month (from installation or start of month)
        days_in_current_month = (now - now.replace(day=1)).days + 1
        if install_date and install_date.month == now.month and install_date.year == now.year:
            effective_days_this_month = (now - install_date).days + 1
        else:
            effective_days_this_month = days_in_current_month
        
        # Performance based on effective days
        effective_prognosis = (prognosis / 30) * effective_days_this_month if prognosis > 0 else 0
        performance = (total_gen / effective_prognosis * 100) if effective_prognosis > 0 else 0
        
        # Get client name and contact
        client = await db.clients.find_one({'id': plant['client_id']}, {'_id': 0, 'name': 1, 'contact_person': 1})
        
        # Get total generation for 12 months (only after installation)
        year_ago = (now - timedelta(days=365)).strftime('%Y-%m-%d')
        query_12m_start = year_ago
        if install_date and install_date.strftime('%Y-%m-%d') > year_ago:
            query_12m_start = install_date.strftime('%Y-%m-%d')
        
        gen_12m = await db.generation_data.find({
            'plant_id': plant['id'],
            'date': {'$gte': query_12m_start}
        }, {'_id': 0, 'generation_kwh': 1}).to_list(10000)
        total_gen_12m = sum(d.get('generation_kwh', 0) for d in gen_12m)
        
        cap = plant.get('capacity_kwp', 0)
        total_capacity_mwp += cap / 1000
        total_gen_all += total_gen_12m
        
        # Calculate performance for different periods: 1D, 15D, 30D, 12M
        # Only count days after installation date
        yesterday_str = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        d15_str = (now - timedelta(days=15)).strftime('%Y-%m-%d')
        d30_str = (now - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Calculate effective days for each period (considering installation date)
        def calc_effective_days(period_start_str: str, period_days: int):
            """Calculate effective days in period after installation."""
            if not install_date:
                return period_days
            period_start = datetime.strptime(period_start_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            if install_date > now:
                return 0
            if install_date <= period_start:
                return period_days
            # Installation is within the period
            return max(0, (now - install_date).days + 1)
        
        effective_1d = 1 if not install_date or install_date <= datetime.strptime(yesterday_str, '%Y-%m-%d').replace(tzinfo=timezone.utc) else 0
        effective_15d = calc_effective_days(d15_str, 15)
        effective_30d = calc_effective_days(d30_str, 30)
        effective_12m = calc_effective_days((now - timedelta(days=365)).strftime('%Y-%m-%d'), 365)
        
        # Get generation data for each period (only after installation)
        gen_1d_query = {'plant_id': plant['id'], 'date': yesterday_str}
        if install_date and install_date.strftime('%Y-%m-%d') > yesterday_str:
            gen_1d_query['date'] = {'$gte': install_date.strftime('%Y-%m-%d'), '$lte': yesterday_str}
        
        gen_1d = await db.generation_data.find(gen_1d_query, {'_id': 0, 'generation_kwh': 1}).to_list(1)
        
        q15_start = max(d15_str, install_date.strftime('%Y-%m-%d') if install_date else d15_str)
        gen_15d = await db.generation_data.find(
            {'plant_id': plant['id'], 'date': {'$gte': q15_start}}, {'_id': 0, 'generation_kwh': 1}
        ).to_list(100)
        
        q30_start = max(d30_str, install_date.strftime('%Y-%m-%d') if install_date else d30_str)
        gen_30d = await db.generation_data.find(
            {'plant_id': plant['id'], 'date': {'$gte': q30_start}}, {'_id': 0, 'generation_kwh': 1}
        ).to_list(100)
        
        gen_1d_total = sum(d.get('generation_kwh',0) for d in gen_1d)
        gen_15d_total = sum(d.get('generation_kwh',0) for d in gen_15d)
        gen_30d_total = sum(d.get('generation_kwh',0) for d in gen_30d)
        
        daily_prog = prognosis / 30 if prognosis > 0 else 0
        
        # Performance = actual / expected, where expected is based on effective days
        perf_1d = round(gen_1d_total / daily_prog * 100) if daily_prog > 0 and effective_1d > 0 else 0
        perf_15d = round(gen_15d_total / (daily_prog * effective_15d) * 100) if daily_prog > 0 and effective_15d > 0 else 0
        perf_30d = round(gen_30d_total / (daily_prog * effective_30d) * 100) if daily_prog > 0 and effective_30d > 0 else 0
        
        # 12M performance based on effective months
        effective_months_12m = effective_12m / 30.4  # Average days per month
        perf_12m = round(total_gen_12m / (prognosis * effective_months_12m) * 100) if prognosis > 0 and effective_months_12m > 0 else 0

        summaries.append({
            'id': plant['id'],
            'name': plant['name'],
            'client_name': client.get('name', 'N/A') if client else 'N/A',
            'contact_person': client.get('contact_person') if client else None,
            'city': plant.get('city', ''),
            'state': plant.get('state', ''),
            'capacity_kwp': cap,
            'installation_date': plant.get('installation_date', ''),
            'status': plant.get('growatt_status') or plant.get('status', 'unknown'),
            'generation_kwh': round(total_gen, 2),
            'generation_12m_kwh': round(total_gen_12m, 2),
            'prognosis_kwh': prognosis,
            'performance': round(performance, 1),
            'perf_1d': perf_1d,
            'perf_15d': perf_15d,
            'perf_30d': perf_30d,
            'perf_12m': perf_12m,
            # Raw kWh for display when no prognosis
            'gen_1d_kwh': round(gen_1d_total, 0),
            'gen_15d_kwh': round(gen_15d_total, 0),
            'gen_30d_kwh': round(gen_30d_total, 0),
            'gen_12m_kwh': round(total_gen_12m, 0),
            'logo_url': plant.get('logo_url'),
            'growatt_plant_id': plant.get('growatt_plant_id'),
            'last_sync': plant.get('last_growatt_sync'),
            'has_growatt': bool(plant.get('growatt_username')),
            # Debug info for effective days
            'effective_days_15d': effective_15d,
            'effective_days_30d': effective_30d,
        })
    
    return {
        'plants': summaries,
        'totals': {
            'total_plants': len(plants),
            'total_capacity_mwp': round(total_capacity_mwp, 2),
            'total_generation_gwh': round(total_gen_all / 1000000, 2),
        }
    }

@api_router.get("/dashboard/generation-chart/{plant_id}")
async def get_generation_chart(
    plant_id: str,
    month: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    if not month:
        month = today_brazil().strftime('%Y-%m')
    
    # Get all days in the month
    year, mon = map(int, month.split('-'))
    import calendar
    days_in_month = calendar.monthrange(year, mon)[1]
    
    # Get generation data
    start_date = f"{month}-01"
    end_date = f"{month}-{days_in_month:02d}"
    
    gen_data = await db.generation_data.find({
        'plant_id': plant_id,
        'date': {'$gte': start_date, '$lte': end_date}
    }, {'_id': 0}).to_list(100)
    
    # Create dict for quick lookup
    gen_dict = {d['date']: d['generation_kwh'] for d in gen_data}
    
    # Get plant for prognosis
    plant = await db.plants.find_one({'id': plant_id}, {'_id': 0, 'monthly_prognosis_kwh': 1, 'capacity_kwp': 1, 'city': 1})
    flat_prog = (plant.get('monthly_prognosis_kwh') or 0) if plant else 0
    
    # Calculate month-specific prognosis from irradiance
    kwp = plant.get('capacity_kwp', 0) if plant else 0
    city_name = plant.get('city', '') if plant else ''
    month_prog = flat_prog
    if city_name and kwp:
        city_doc = await db.irradiance_cities.find_one(
            {'city': {'$regex': f'^{city_name}$', '$options': 'i'}}, {'_id': 0}
        )
        if city_doc:
            months_key = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
            irr_val = city_doc.get('irradiance', {}).get(months_key[mon - 1], 0)
            irr_prog = round(kwp * days_in_month * ((irr_val / 1000) - 0.1) * 0.75, 2)
            if irr_prog > 0:
                month_prog = irr_prog
    
    daily_prognosis = month_prog / days_in_month if month_prog > 0 else 0
    
    # Build chart data
    chart_data = []
    for day in range(1, days_in_month + 1):
        date_str = f"{month}-{day:02d}"
        chart_data.append({
            'day': day,
            'date': date_str,
            'generation': gen_dict.get(date_str, 0),
            'prognosis': round(daily_prognosis, 2)
        })
    
    return {'chart': chart_data, 'month_prognosis': round(month_prog, 2), 'total_generation': round(sum(gen_dict.values()), 2), 'days_in_month': days_in_month}

@api_router.get("/dashboard/power-curve/{plant_id}")
async def get_power_curve(
    plant_id: str,
    date: Optional[str] = None,
    force_real: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Get intraday power curve (kW) for a plant on a specific date.
    By default returns simulated curve based on daily generation.
    Use force_real=true to attempt fetching real data from Growatt (slower).
    """
    import math
    
    if not date:
        date = today_brazil().strftime('%Y-%m-%d')
    
    # Get plant info
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True}, {'_id': 0})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    
    # Get generation data for the date
    gen_data = await db.generation_data.find_one(
        {'plant_id': plant_id, 'date': date},
        {'_id': 0}
    )
    
    total_kwh = gen_data.get('generation_kwh', 0) if gen_data else 0
    capacity_kwp = plant.get('capacity_kwp', 0)
    
    # Generate simulated power curve based on total daily generation
    # This is a fast response that doesn't require Growatt login
    curve = []
    peak_kw = 0
    
    if total_kwh > 0:
        # Use sine wave model to distribute energy throughout the day
        # Peak is at solar noon (12:00), with generation from 5:00 to 18:00
        peak_kw = total_kwh * math.pi / (2 * 12.5)  # Calculate peak from total energy
        
        for hour in range(5, 19):
            for minute in [0, 15, 30, 45]:
                time_str = f"{hour:02d}:{minute:02d}"
                t = hour + minute/60
                
                # Calculate power based on sine wave, centered at 11:30
                angle = math.pi * (t - 5) / 13  # 0 to pi over 13-hour span
                power_kw = peak_kw * math.sin(angle) if 0 <= angle <= math.pi else 0
                
                # For today, only show points up to current time (Brazil timezone)
                if date == today_brazil().strftime('%Y-%m-%d'):
                    now_brazil_time = now_brazil()
                    now_hour = now_brazil_time.hour
                    now_minute = now_brazil_time.minute
                    if hour > now_hour or (hour == now_hour and minute > now_minute):
                        continue
                
                if power_kw > 0:
                    curve.append({
                        'time': time_str,
                        'power_kw': round(max(0, power_kw), 2)
                    })
    
    # Calculate performance
    prognosis = plant.get('monthly_prognosis_kwh', 0)
    daily_prognosis = prognosis / 30 if prognosis > 0 else 0
    performance = (total_kwh / daily_prognosis * 100) if daily_prognosis > 0 and total_kwh > 0 else 0
    
    return {
        'plant_name': plant.get('name', ''),
        'date': date,
        'capacity_kwp': capacity_kwp,
        'total_kwh': round(total_kwh, 2),
        'peak_kw': round(peak_kw, 2),
        'performance': round(performance, 1),
        'status': plant.get('growatt_status') or plant.get('status', 'unknown'),
        'curve': curve,
        'source': 'estimated'  # Indicate this is an estimate based on daily total
    }

# ==================== CREDIT DISTRIBUTION LISTS ====================

@api_router.get("/credit-distribution/{plant_id}")
async def get_credit_distribution_lists(plant_id: str, current_user: dict = Depends(get_current_user)):
    """Get all credit distribution lists for a plant"""
    lists = await db.credit_distribution_lists.find(
        {'plant_id': plant_id, 'is_active': True},
        {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    
    for lst in lists:
        if isinstance(lst.get('created_at'), str):
            lst['created_at'] = datetime.fromisoformat(lst['created_at'])
    
    return lists

@api_router.post("/credit-distribution")
async def create_credit_distribution_list(
    list_data: CreditDistributionListCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new credit distribution list"""
    # Verify plant exists
    plant = await db.plants.find_one({'id': list_data.plant_id, 'is_active': True})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    
    dist_list = CreditDistributionList(**list_data.model_dump())
    doc = dist_list.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.credit_distribution_lists.insert_one(doc)
    
    # Log activity
    await log_activity(list_data.plant_id, "created_distribution_list", 
                      f"Lista de distribuição criada: {list_data.name}", 
                      current_user.get('name'))
    
    return dist_list

@api_router.put("/credit-distribution/{list_id}")
async def update_credit_distribution_list(
    list_id: str,
    list_data: CreditDistributionListCreate,
    current_user: dict = Depends(get_current_user)
):
    """Update a credit distribution list"""
    result = await db.credit_distribution_lists.update_one(
        {'id': list_id, 'is_active': True},
        {'$set': list_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lista não encontrada")
    
    updated = await db.credit_distribution_lists.find_one({'id': list_id}, {'_id': 0})
    return updated

@api_router.delete("/credit-distribution/{list_id}")
async def delete_credit_distribution_list(list_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a credit distribution list"""
    result = await db.credit_distribution_lists.update_one(
        {'id': list_id},
        {'$set': {'is_active': False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lista não encontrada")
    return {"message": "Lista removida com sucesso"}

# ==================== MONTHLY REPORTS ====================

@api_router.get("/reports/{plant_id}")
async def get_monthly_reports(
    plant_id: str,
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get monthly reports for a plant"""
    query = {'plant_id': plant_id}
    if year:
        query['year'] = year
    
    reports = await db.monthly_reports.find(query, {'_id': 0}).sort([('year', -1), ('month', -1)]).to_list(100)
    
    for r in reports:
        if isinstance(r.get('created_at'), str):
            r['created_at'] = datetime.fromisoformat(r['created_at'])
        if r.get('generated_at') and isinstance(r['generated_at'], str):
            r['generated_at'] = datetime.fromisoformat(r['generated_at'])
    
    return reports

@api_router.post("/reports")
async def create_or_update_monthly_report(
    report_data: MonthlyReportCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create or update a monthly report"""
    # Check if report already exists
    existing = await db.monthly_reports.find_one({
        'plant_id': report_data.plant_id,
        'year': report_data.year,
        'month': report_data.month
    })
    
    if existing:
        # Update existing
        await db.monthly_reports.update_one(
            {'id': existing['id']},
            {'$set': report_data.model_dump()}
        )
        updated = await db.monthly_reports.find_one({'id': existing['id']}, {'_id': 0})
        return updated
    else:
        # Create new
        report = MonthlyReport(**report_data.model_dump())
        doc = report.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        if doc.get('generated_at'):
            doc['generated_at'] = doc['generated_at'].isoformat()
        await db.monthly_reports.insert_one(doc)
        return report

@api_router.get("/reports/{plant_id}/years")
async def get_available_report_years(plant_id: str, current_user: dict = Depends(get_current_user)):
    """Get list of years with reports for a plant"""
    pipeline = [
        {'$match': {'plant_id': plant_id}},
        {'$group': {'_id': '$year'}},
        {'$sort': {'_id': -1}}
    ]
    result = await db.monthly_reports.aggregate(pipeline).to_list(100)
    years = [r['_id'] for r in result if r['_id']]
    
    # Always include current year
    current_year = datetime.now().year
    if current_year not in years:
        years.insert(0, current_year)
    
    return sorted(years, reverse=True)

# ==================== ACTIVITY LOG ====================

async def log_activity(plant_id: str, action: str, description: str, user_name: Optional[str] = None, details: Optional[Dict] = None):
    """Helper to log activities"""
    activity = ActivityLog(
        plant_id=plant_id,
        action=action,
        description=description,
        user_name=user_name,
        details=details
    )
    doc = activity.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.activity_logs.insert_one(doc)

@api_router.get("/activity/{plant_id}")
async def get_activity_log(
    plant_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get activity log for a plant"""
    activities = await db.activity_logs.find(
        {'plant_id': plant_id},
        {'_id': 0}
    ).sort('created_at', -1).limit(limit).to_list(limit)
    
    for a in activities:
        if isinstance(a.get('created_at'), str):
            a['created_at'] = datetime.fromisoformat(a['created_at'])
    
    return activities

@api_router.post("/activity")
async def create_activity(
    plant_id: str,
    action: str,
    description: str,
    current_user: dict = Depends(get_current_user)
):
    """Create a manual activity log entry"""
    await log_activity(plant_id, action, description, current_user.get('name'))
    return {"success": True}

# ==================== PLANT DETAILS (EXTENDED) ====================

@api_router.get("/plants/{plant_id}/full-details")
async def get_plant_full_details(plant_id: str, current_user: dict = Depends(get_current_user)):
    """Get complete plant details including client, UCs, reports, etc."""
    # Get plant
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True}, {'_id': 0})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    
    # Get client
    client = await db.clients.find_one({'id': plant.get('client_id'), 'is_active': True}, {'_id': 0})
    
    # Get consumer units
    units = await db.consumer_units.find({'plant_id': plant_id, 'is_active': True}, {'_id': 0}).to_list(100)
    
    # Separate generators and beneficiaries
    generators = [u for u in units if u.get('is_generator')]
    beneficiaries = [u for u in units if not u.get('is_generator')]
    
    # Get credit distribution lists
    credit_lists = await db.credit_distribution_lists.find(
        {'plant_id': plant_id, 'is_active': True}, {'_id': 0}
    ).sort('created_at', -1).to_list(10)
    
    # Get latest reports (current year)
    current_year = datetime.now().year
    reports = await db.monthly_reports.find(
        {'plant_id': plant_id, 'year': current_year}, {'_id': 0}
    ).sort('month', -1).to_list(12)
    
    # Get generation stats for last 12 months
    twelve_months_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    gen_data = await db.generation_data.find({
        'plant_id': plant_id,
        'date': {'$gte': twelve_months_ago}
    }, {'_id': 0}).to_list(10000)
    
    total_gen_12m = sum(d.get('generation_kwh', 0) for d in gen_data)
    
    # Get recent activity
    activities = await db.activity_logs.find(
        {'plant_id': plant_id}, {'_id': 0}
    ).sort('created_at', -1).limit(20).to_list(20)
    
    return {
        "plant": plant,
        "client": client,
        "generators": generators,
        "beneficiaries": beneficiaries,
        "credit_distribution_lists": credit_lists,
        "reports": reports,
        "stats": {
            "total_generation_12m_kwh": round(total_gen_12m, 2),
            "capacity_kwp": plant.get('capacity_kwp', 0),
            "status": plant.get('status', 'online'),
            "generator_count": len(generators),
            "beneficiary_count": len(beneficiaries)
        },
        "activities": activities
    }



@api_router.post("/inverter-credentials")
async def create_inverter_credential(cred_data: InverterCredentialCreate, current_user: dict = Depends(get_current_user)):
    # In production, encrypt password with AES-256
    # For now, we'll store a placeholder
    cred = InverterCredential(
        plant_id=cred_data.plant_id,
        brand=cred_data.brand,
        username=cred_data.username
    )
    doc = cred.model_dump()
    doc['encrypted_password'] = hash_password(cred_data.password)  # Simple hash for demo
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('last_sync'):
        doc['last_sync'] = doc['last_sync'].isoformat()
    
    await db.inverter_credentials.insert_one(doc)
    return cred

@api_router.get("/inverter-credentials/{plant_id}")
async def get_inverter_credentials(plant_id: str, current_user: dict = Depends(get_current_user)):
    creds = await db.inverter_credentials.find({'plant_id': plant_id, 'is_active': True}, {'_id': 0, 'encrypted_password': 0}).to_list(100)
    for c in creds:
        if isinstance(c.get('created_at'), str):
            c['created_at'] = datetime.fromisoformat(c['created_at'])
        if c.get('last_sync') and isinstance(c['last_sync'], str):
            c['last_sync'] = datetime.fromisoformat(c['last_sync'])
    return creds

# ==================== COPEL AVA INTEGRATION ====================

from services.copel_ava_service import CopelAVAService

@api_router.post("/integrations/copel/save-credentials")
async def save_copel_credentials(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Save COPEL AVA credentials for a plant."""
    plant_id = request.get('plant_id', '')
    cnpj = request.get('cnpj', '')
    password = request.get('password', '')

    plant = await db.plants.find_one({'id': plant_id, 'is_active': True})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina nao encontrada")

    await db.plants.update_one({'id': plant_id}, {'$set': {
        'copel_cnpj': cnpj,
        'copel_password': password,
        'copel_integration': True,
    }})
    return {"success": True, "message": "Credenciais COPEL salvas"}


@api_router.post("/integrations/copel/check-invoices/{plant_id}")
async def check_copel_invoices(
    plant_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Login to COPEL and check available invoices for all UCs of a plant."""
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True}, {'_id': 0})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina nao encontrada")

    cnpj = plant.get('copel_cnpj', '')
    password = plant.get('copel_password', '')
    if not cnpj or not password:
        raise HTTPException(status_code=400, detail="Credenciais COPEL nao configuradas. Va em Configuracoes.")

    service = CopelAVAService()
    try:
        login_result = await service.login(cnpj, password)
        if not login_result.get('success'):
            raise HTTPException(status_code=400, detail=login_result.get('error', 'Login COPEL falhou'))

        # Get UCs for this plant
        units = await db.consumer_units.find(
            {'plant_id': plant_id, 'is_active': True},
            {'_id': 0, 'uc_number': 1, 'id': 1}
        ).to_list(100)

        all_invoices = []
        for unit in units:
            uc = unit.get('uc_number', '')
            if uc:
                invoices = await service.list_available_invoices(uc)
                all_invoices.extend(invoices)

        return {
            "success": True,
            "total_invoices": len(all_invoices),
            "invoices": all_invoices,
        }
    finally:
        await service.close()


@api_router.post("/integrations/copel/download-invoice/{plant_id}")
async def download_copel_invoice(
    plant_id: str,
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Download and process a specific invoice from COPEL."""
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True}, {'_id': 0})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina nao encontrada")

    cnpj = plant.get('copel_cnpj', '')
    password = plant.get('copel_password', '')
    uc_number = request.get('uc_number', '')
    reference_month = request.get('reference_month', '')

    if not cnpj or not password:
        raise HTTPException(status_code=400, detail="Credenciais COPEL nao configuradas")

    service = CopelAVAService()
    try:
        login_result = await service.login(cnpj, password)
        if not login_result.get('success'):
            raise HTTPException(status_code=400, detail="Login COPEL falhou")

        pdf_data = await service.download_invoice(uc_number, reference_month)
        if not pdf_data:
            raise HTTPException(status_code=404, detail=f"Fatura nao disponivel para UC {uc_number} ref {reference_month}")

        # Parse the downloaded PDF
        from services.pdf_parser_service import parse_copel_invoice
        from io import BytesIO
        parsed = parse_copel_invoice(BytesIO(pdf_data))

        if parsed.get('success'):
            # Find consumer unit
            unit = await db.consumer_units.find_one(
                {'uc_number': uc_number, 'plant_id': plant_id, 'is_active': True},
                {'_id': 0}
            )
            if unit:
                parsed['consumer_unit_id'] = unit['id']
                parsed['plant_id'] = plant_id
                parsed['source'] = 'copel_auto'

        return {
            "success": True,
            "parsed_data": parsed,
            "pdf_size": len(pdf_data),
            "message": f"Fatura baixada e processada: UC {uc_number} ref {reference_month}",
        }
    finally:
        await service.close()


# ==================== COPEL CREDENTIALS ====================

@api_router.post("/copel-credentials")
async def create_copel_credential(cred_data: CopelCredentialCreate, current_user: dict = Depends(get_current_user)):
    cred = CopelCredential(
        consumer_unit_id=cred_data.consumer_unit_id,
        cpf=cred_data.cpf
    )
    doc = cred.model_dump()
    doc['encrypted_password'] = hash_password(cred_data.password)
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('last_sync'):
        doc['last_sync'] = doc['last_sync'].isoformat()
    
    await db.copel_credentials.insert_one(doc)
    return cred

@api_router.get("/copel-credentials/{consumer_unit_id}")
async def get_copel_credentials(consumer_unit_id: str, current_user: dict = Depends(get_current_user)):
    cred = await db.copel_credentials.find_one(
        {'consumer_unit_id': consumer_unit_id, 'is_active': True},
        {'_id': 0, 'encrypted_password': 0}
    )
    if not cred:
        return None
    if isinstance(cred.get('created_at'), str):
        cred['created_at'] = datetime.fromisoformat(cred['created_at'])
    if cred.get('last_sync') and isinstance(cred['last_sync'], str):
        cred['last_sync'] = datetime.fromisoformat(cred['last_sync'])
    return cred

# ==================== CLIENT LOGINS ====================

@api_router.get("/client-logins")
async def get_client_logins(current_user: dict = Depends(get_current_user)):
    """Get all client logins"""
    logins = await db.client_logins.find({}, {'_id': 0}).to_list(1000)
    return logins

@api_router.post("/client-logins", response_model=ClientLogin)
async def create_client_login(login_data: ClientLoginCreate, current_user: dict = Depends(get_current_user)):
    """Create a new client login"""
    login = ClientLogin(**login_data.model_dump())
    doc = login.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.client_logins.insert_one(doc)
    return login

@api_router.put("/client-logins/{login_id}")
async def update_client_login(login_id: str, login_data: ClientLoginCreate, current_user: dict = Depends(get_current_user)):
    """Update a client login"""
    result = await db.client_logins.update_one(
        {'id': login_id},
        {'$set': login_data.model_dump()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Login não encontrado")
    return {"status": "updated"}

@api_router.delete("/client-logins/{login_id}")
async def delete_client_login(login_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a client login"""
    result = await db.client_logins.delete_one({'id': login_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Login não encontrado")
    return {"status": "deleted"}

@api_router.post("/client-logins/upload-excel")
async def upload_client_logins_excel(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Import client logins from CSV/Excel file"""
    import csv
    import io
    
    content = await file.read()
    
    # Try to decode as UTF-8
    try:
        text = content.decode('utf-8')
    except:
        text = content.decode('latin-1')
    
    # Parse CSV
    reader = csv.DictReader(io.StringIO(text))
    
    imported = 0
    errors = []
    
    for row in reader:
        try:
            # Map columns (support both English and Portuguese names)
            login_data = {
                'inverter_app': row.get('inverter_app') or row.get('app') or row.get('portal') or '',
                'on_unit': row.get('on_unit') or row.get('unidade') or '',
                'client_name': row.get('client_name') or row.get('cliente') or row.get('nome') or '',
                'login': row.get('login') or row.get('usuario') or row.get('email') or '',
                'password': row.get('password') or row.get('senha') or '',
                'site_url': row.get('site_url') or row.get('url') or row.get('site') or '',
                'is_installer': str(row.get('is_installer', 'false')).lower() in ('true', '1', 'sim', 'yes')
            }
            
            if not login_data['inverter_app'] or not login_data['login'] or not login_data['password']:
                errors.append(f"Linha incompleta: {row}")
                continue
            
            login = ClientLogin(**login_data)
            doc = login.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.client_logins.insert_one(doc)
            imported += 1
            
        except Exception as e:
            errors.append(f"Erro na linha {row}: {str(e)}")
    
    return {
        "imported": imported,
        "errors": errors[:10] if errors else []  # Return first 10 errors
    }

# ==================== SYNC SETTINGS ====================

@api_router.get("/settings/sync-interval")
async def get_sync_interval(current_user: dict = Depends(get_current_user)):
    """Get the current Growatt sync interval in minutes."""
    settings = await db.app_settings.find_one({'key': 'growatt_sync_interval'}, {'_id': 0})
    if settings:
        return {"interval_minutes": int(settings.get('value', 30)), "updated_at": settings.get('updated_at')}
    return {"interval_minutes": 30, "updated_at": None}

@api_router.put("/settings/sync-interval")
async def update_sync_interval(data: dict, current_user: dict = Depends(get_current_user)):
    """Update the Growatt sync interval in minutes."""
    interval = int(data.get('interval_minutes', 30))
    if interval < 5:
        raise HTTPException(status_code=400, detail="Intervalo mínimo é 5 minutos")
    if interval > 1440:
        raise HTTPException(status_code=400, detail="Intervalo máximo é 1440 minutos (24 horas)")
    
    from services.scheduler import set_sync_interval
    success = await set_sync_interval(interval)
    
    if success:
        return {"status": "updated", "interval_minutes": interval}
    else:
        raise HTTPException(status_code=500, detail="Erro ao atualizar intervalo")

@api_router.get("/settings/sync-status")
async def get_sync_status(current_user: dict = Depends(get_current_user)):
    """Get the current sync status and next scheduled run."""
    from services.scheduler import get_scheduler, get_current_interval
    
    scheduler = get_scheduler()
    next_run = None
    
    if scheduler:
        job = scheduler.get_job('sync_growatt_interval')
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()
    
    # Get last sync time from any plant
    last_sync_plant = await db.plants.find_one(
        {'last_growatt_sync': {'$exists': True}},
        {'_id': 0, 'last_growatt_sync': 1},
        sort=[('last_growatt_sync', -1)]
    )
    last_sync = last_sync_plant.get('last_growatt_sync') if last_sync_plant else None
    
    # Count plants with Growatt credentials
    growatt_count = await db.plants.count_documents({
        'growatt_username': {'$exists': True, '$ne': ''},
        'is_active': True
    })
    
    return {
        "interval_minutes": get_current_interval(),
        "next_run": next_run,
        "last_sync": last_sync,
        "plants_with_credentials": growatt_count
    }

@api_router.post("/sync/growatt/all")
async def sync_all_growatt_now(current_user: dict = Depends(get_current_user)):
    """Manually trigger Growatt sync for all plants."""
    from services.scheduler import sync_all_growatt_plants
    
    # Run in background using asyncio.create_task (not BackgroundTasks, which runs sync)
    asyncio.create_task(sync_all_growatt_plants())
    
    return {"status": "started", "message": "Sincronização iniciada em background"}

# ==================== REPORT DATA ====================

@api_router.get("/reports/plant/{plant_id}")
async def get_plant_report_data(
    plant_id: str,
    month: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all data needed for a plant report"""
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True}, {'_id': 0})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    
    # Get client
    client = await db.clients.find_one({'id': plant['client_id']}, {'_id': 0})
    
    # Parse month
    year, mon = map(int, month.split('-'))
    import calendar
    days_in_month = calendar.monthrange(year, mon)[1]
    start_date = f"{month}-01"
    end_date = f"{month}-{days_in_month:02d}"
    
    # Get generation data for the month
    gen_data = await db.generation_data.find({
        'plant_id': plant_id,
        'date': {'$gte': start_date, '$lte': end_date}
    }, {'_id': 0}).sort('date', 1).to_list(100)
    
    total_generation = sum(d['generation_kwh'] for d in gen_data)
    prognosis = plant.get('monthly_prognosis_kwh') or 0
    performance = (total_generation / prognosis * 100) if prognosis > 0 else 0
    
    # Get consumer units
    consumer_units = await db.consumer_units.find({'plant_id': plant_id, 'is_active': True}, {'_id': 0}).to_list(100)
    
    # Get invoices for consumer units
    unit_ids = [u['id'] for u in consumer_units]
    invoices = await db.invoices.find({
        'consumer_unit_id': {'$in': unit_ids},
        'billing_cycle_end': {'$gte': start_date, '$lte': end_date}
    }, {'_id': 0}).to_list(1000)
    
    total_saved = sum(i.get('amount_saved_brl', 0) for i in invoices)
    total_billed = sum(i.get('amount_billed_brl', 0) for i in invoices)
    
    # Calculate environmental impact
    co2_avoided = total_generation * 0.5  # kg
    trees_saved = co2_avoided / 22  # trees/year equivalent
    
    # Get historical data (last 12 months)
    historical = []
    for i in range(12):
        hist_date = datetime(year, mon, 1) - timedelta(days=30*i)
        hist_month = hist_date.strftime('%Y-%m')
        hist_start = f"{hist_month}-01"
        hist_days = calendar.monthrange(hist_date.year, hist_date.month)[1]
        hist_end = f"{hist_month}-{hist_days:02d}"
        
        hist_gen = await db.generation_data.find({
            'plant_id': plant_id,
            'date': {'$gte': hist_start, '$lte': hist_end}
        }, {'_id': 0, 'generation_kwh': 1}).to_list(100)
        
        hist_total = sum(d['generation_kwh'] for d in hist_gen)
        historical.append({
            'month': hist_month,
            'generation_kwh': round(hist_total, 2),
            'prognosis_kwh': prognosis
        })
    
    # Calculate ROI if investment is set
    total_investment = plant.get('total_investment', 0)
    roi_monthly = (total_saved / total_investment * 100) if total_investment > 0 else 0
    
    # Get total savings since installation
    all_invoices = await db.invoices.find({'plant_id': plant_id}, {'_id': 0, 'amount_saved_brl': 1}).to_list(10000)
    total_savings_all_time = sum(i.get('amount_saved_brl', 0) for i in all_invoices)
    roi_total = (total_savings_all_time / total_investment * 100) if total_investment > 0 else 0
    
    return {
        'plant': plant,
        'client': client,
        'month': month,
        'generation': {
            'total_kwh': round(total_generation, 2),
            'prognosis_kwh': prognosis,
            'performance_percent': round(performance, 1),
            'daily_data': gen_data
        },
        'financial': {
            'saved_brl': round(total_saved, 2),
            'billed_brl': round(total_billed, 2),
            'roi_monthly_percent': round(roi_monthly, 2),
            'roi_total_percent': round(roi_total, 2),
            'total_savings_all_time': round(total_savings_all_time, 2)
        },
        'environmental': {
            'co2_avoided_kg': round(co2_avoided, 2),
            'co2_avoided_tons': round(co2_avoided / 1000, 2),
            'trees_saved': round(trees_saved, 0)
        },
        'consumer_units': consumer_units,
        'invoices': invoices,
        'historical': list(reversed(historical))
    }


@api_router.get("/plants/{plant_id}/monthly-summary")
async def get_monthly_summary(
    plant_id: str,
    year: int,
    current_user: dict = Depends(get_current_user)
):
    """Get monthly generation summary for a plant for a given year."""
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True}, {'_id': 0})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina nao encontrada")

    flat_prognosis = plant.get('monthly_prognosis_kwh') or 0
    kwp = plant.get('capacity_kwp', 0)
    city_name = plant.get('city', '')

    # Try to get per-month prognosis from irradiance data
    month_prognosis = {}
    if city_name and kwp:
        city_doc = await db.irradiance_cities.find_one(
            {'city': {'$regex': f'^{city_name}$', '$options': 'i'}},
            {'_id': 0}
        )
        if city_doc:
            irr = city_doc.get('irradiance', {})
            months_key = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
            for i, mk in enumerate(months_key):
                irr_val = irr.get(mk, 0)
                import calendar as cal_mod_inner
                m_days = cal_mod_inner.monthrange(year, i+1)[1]
                month_prognosis[i+1] = round(kwp * m_days * ((irr_val / 1000) - 0.1) * 0.75, 2)

    import calendar as cal_mod
    now = datetime.now(timezone.utc)
    current_year = now.year
    current_month = now.month
    current_day = now.day

    # Get all UCs for this plant
    units = await db.consumer_units.find({'plant_id': plant_id, 'is_active': True}, {'_id': 0, 'id': 1, 'uc_number': 1}).to_list(100)
    uc_numbers = [u.get('uc_number','') for u in units if u.get('uc_number')]
    unit_ids = [u['id'] for u in units]
    # Also get UC IDs from other plants with same uc_numbers
    all_matching = await db.consumer_units.find({'uc_number': {'$in': uc_numbers}}, {'_id': 0, 'id': 1, 'uc_number': 1}).to_list(500)
    all_uc_ids = list(set(unit_ids + [u['id'] for u in all_matching]))

    # Pre-build map: uc_number -> set of all consumer_unit_ids across plants
    ucnum_to_ids = {}
    for u in units:
        ucn = u.get('uc_number','')
        if ucn:
            ucnum_to_ids.setdefault(ucn, set()).add(u['id'])
    for m in all_matching:
        ucn = m.get('uc_number','')
        if ucn:
            ucnum_to_ids.setdefault(ucn, set()).add(m['id'])

    monthly_result = []

    for month in range(1, 13):
        days = cal_mod.monthrange(year, month)[1]
        start = f"{year}-{month:02d}-01"
        end = f"{year}-{month:02d}-{days:02d}"

        gen_docs = await db.generation_data.find(
            {'plant_id': plant_id, 'date': {'$gte': start, '$lte': end}},
            {'_id': 0, 'generation_kwh': 1}
        ).to_list(100)

        gen_total = sum(d.get('generation_kwh', 0) for d in gen_docs)
        prog = month_prognosis.get(month, flat_prognosis) or 0

        # For current month: prognosis proportional to days elapsed
        if year == current_year and month == current_month:
            prog_daily = prog / days if prog > 0 else 0
            prog_adjusted = prog_daily * current_day
            perf = (gen_total / prog_adjusted * 100) if prog_adjusted > 0 else 0
        else:
            perf = (gen_total / prog * 100) if prog > 0 else 0

        # Get invoice status per UC for this month
        ref_month = f"{month:02d}/{year}"
        month_invoices = await db.invoices.find({
            '$or': [
                {'consumer_unit_id': {'$in': all_uc_ids}, 'reference_month': ref_month},
                {'plant_id': plant_id, 'reference_month': ref_month},
            ]
        }, {'_id': 0, 'consumer_unit_id': 1}).to_list(500)
        invoice_uc_ids = set(inv.get('consumer_unit_id','') for inv in month_invoices)

        # Build UC status using pre-built ucnum_to_ids map
        uc_status = []
        for u in units:
            ucn = u.get('uc_number','')
            possible_ids = ucnum_to_ids.get(ucn, {u['id']})
            has = bool(possible_ids & invoice_uc_ids)
            uc_status.append({'uc': ucn, 'has_invoice': has})

        monthly_result.append({
            'month': month,
            'year': year,
            'generation_kwh': round(gen_total, 2),
            'prognosis_kwh': prog,
            'performance_percent': round(perf, 1),
            'uc_status': uc_status,
        })

    return monthly_result


# ==================== IRRADIANCE / PROGNOSIS ====================

@api_router.get("/irradiance/states")
async def list_irradiance_states(current_user: dict = Depends(get_current_user)):
    """List all available states."""
    states = await db.irradiance_cities.distinct('state')
    states.sort()
    return states


# State abbreviation to full name mapping for irradiance search
STATE_ABBREV_MAP = {
    'AC': 'ACRE', 'AL': 'ALAGOAS', 'AP': 'AMAPÁ', 'AM': 'AMAZONAS',
    'BA': 'BAHIA', 'CE': 'CEARÁ', 'DF': 'DISTRITO_FEDERAL', 'ES': 'ESPÍRITO_SANTO',
    'GO': 'GOIÁS', 'MA': 'MARANHÃO', 'MT': 'MATO_GROSSO', 'MS': 'MATO_GROSSO_DO_SUL',
    'MG': 'MINAS_GERAIS', 'PA': 'PARÁ', 'PB': 'PARAÍBA', 'PR': 'PARANÁ',
    'PE': 'PERNAMBUCO', 'PI': 'PIAUÍ', 'RJ': 'RIO_DE_JANEIRO', 'RN': 'RIO_GRANDE_DO_NORTE',
    'RS': 'RIO_GRANDE_DO_SUL', 'RO': 'RONDÔNIA', 'RR': 'RORAIMA', 'SC': 'SANTA_CATARINA',
    'SP': 'SÃO_PAULO', 'SE': 'SERGIPE', 'TO': 'TOCANTINS'
}

@api_router.get("/irradiance/cities")
async def search_irradiance_cities(
    q: str = "",
    state: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Search cities by name for irradiance data."""
    query = {}
    if q:
        query['city'] = {'$regex': q, '$options': 'i'}
    if state:
        # Normalize state: convert abbreviation to full name if needed
        state_upper = state.upper().strip()
        normalized_state = STATE_ABBREV_MAP.get(state_upper, state_upper)
        # Also handle cases like "PARANÁ" vs "PARANA" (with/without accents)
        query['state'] = {'$regex': f'^{normalized_state}$', '$options': 'i'}
    limit = 500 if state and not q else 30
    cities = await db.irradiance_cities.find(query, {'_id': 0}).sort('city', 1).limit(limit).to_list(limit)
    return cities


@api_router.get("/irradiance/city/{city_name}")
async def get_city_irradiance(city_name: str, current_user: dict = Depends(get_current_user)):
    """Get irradiance data for a specific city."""
    city = await db.irradiance_cities.find_one(
        {'city': {'$regex': f'^{city_name}$', '$options': 'i'}},
        {'_id': 0}
    )
    if not city:
        raise HTTPException(status_code=404, detail="Cidade nao encontrada")
    return city


@api_router.post("/irradiance/calculate-prognosis")
async def calculate_prognosis(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Calculate monthly prognosis based on city irradiance and plant capacity.
    Formula: kWp * dias_do_mes * ((irradiance/1000) - 0.1) * 0.75
    """
    city_name = request.get('city', '')
    kwp = float(request.get('capacity_kwp', 0))

    city = await db.irradiance_cities.find_one(
        {'city': {'$regex': f'^{city_name}$', '$options': 'i'}},
        {'_id': 0}
    )
    if not city:
        raise HTTPException(status_code=404, detail="Cidade nao encontrada")

    irr = city.get('irradiance', {})
    months = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    result = []
    total_annual = 0

    for i, m in enumerate(months):
        irr_val = irr.get(m, 0)
        days = month_days[i]
        daily = kwp * ((irr_val / 1000) - 0.1) * 0.75
        monthly = daily * days
        total_annual += monthly
        result.append({
            'month': m,
            'irradiance': irr_val,
            'days': days,
            'daily_kwh': round(daily, 2),
            'monthly_kwh': round(monthly, 2),
        })

    avg_monthly = total_annual / 12

    return {
        'city': city['city'],
        'state': city['state'],
        'capacity_kwp': kwp,
        'months': result,
        'average_monthly_kwh': round(avg_monthly, 2),
        'total_annual_kwh': round(total_annual, 2),
    }


# ==================== ROOT ROUTE ====================

@api_router.get("/")
async def root():
    return {"message": "ON Soluções Energéticas API", "version": "1.0.0"}

@api_router.get("/reports/generate-pdf/{plant_id}")
async def generate_pdf_report(
    plant_id: str,
    month: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate PDF report for a plant (placeholder - implementation pending)"""
    # This endpoint will be implemented with a Node.js microservice or Python alternative
    raise HTTPException(
        status_code=501, 
        detail="Geração de PDF em desenvolvimento. Use a prévia do relatório no frontend."
    )

# ==================== COPEL INTEGRATION ====================

from services.copel_service import CopelService, test_copel_login, download_copel_invoice

class CopelLoginRequest(BaseModel):
    cpf_cnpj: str
    password: str

class CopelSyncRequest(BaseModel):
    consumer_unit_id: str
    cpf_cnpj: str
    password: str

@api_router.post("/integrations/copel/test-login")
async def test_copel_login_endpoint(request: CopelLoginRequest, current_user: dict = Depends(get_current_user)):
    """Test COPEL portal credentials"""
    result = await test_copel_login(request.cpf_cnpj, request.password)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Login COPEL falhou'))
    
    return {
        "success": True,
        "message": result.get('message', 'Login realizado com sucesso'),
        "url": result.get('url')
    }

@api_router.post("/integrations/copel/list-ucs")
async def list_copel_ucs_endpoint(request: CopelLoginRequest, current_user: dict = Depends(get_current_user)):
    """List all consumer units (UCs) from COPEL account"""
    service = CopelService()
    try:
        login_result = await service.login(request.cpf_cnpj, request.password)
        if not login_result.get('success'):
            raise HTTPException(status_code=400, detail=login_result.get('error', 'Login COPEL falhou'))
        
        units = await service.get_consumer_units()
        
        return {
            "success": True,
            "ucs": units,
            "total": len(units)
        }
    finally:
        await service.close()

@api_router.post("/integrations/copel/download-invoice")
async def download_copel_invoice_endpoint(request: CopelSyncRequest, current_user: dict = Depends(get_current_user)):
    """Download invoice from COPEL portal"""
    
    # Verify consumer unit exists
    unit = await db.consumer_units.find_one({'id': request.consumer_unit_id, 'is_active': True})
    if not unit:
        raise HTTPException(status_code=404, detail="Unidade consumidora não encontrada")
    
    result = await download_copel_invoice(request.cpf_cnpj, request.password)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Falha ao baixar fatura'))
    
    # Update last sync time
    await db.copel_credentials.update_one(
        {'consumer_unit_id': request.consumer_unit_id},
        {'$set': {'last_sync': datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "success": True,
        "filepath": result.get('filepath'),
        "filename": result.get('filename'),
        "message": "Fatura baixada com sucesso"
    }

@api_router.post("/integrations/copel/sync")
async def sync_copel_data(request: CopelSyncRequest, current_user: dict = Depends(get_current_user)):
    """Sync invoice data from COPEL portal - login, download and parse"""
    
    # Verify consumer unit exists
    unit = await db.consumer_units.find_one({'id': request.consumer_unit_id, 'is_active': True})
    if not unit:
        raise HTTPException(status_code=404, detail="Unidade consumidora não encontrada")
    
    # First, login and download invoice
    download_result = await download_copel_invoice(request.cpf_cnpj, request.password)
    
    if not download_result.get('success'):
        raise HTTPException(status_code=400, detail=download_result.get('error', 'Falha ao sincronizar com COPEL'))
    
    # Update last sync time
    await db.copel_credentials.update_one(
        {'consumer_unit_id': request.consumer_unit_id},
        {'$set': {'last_sync': datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    
    return {
        "success": True,
        "filepath": download_result.get('filepath'),
        "filename": download_result.get('filename'),
        "message": "Sincronização COPEL realizada. Fatura baixada com sucesso."
    }

# ==================== GROWATT INTEGRATION (OSS Portal via Web Scraping) ====================

# Import already done at top of file

class GrowattLoginRequest(BaseModel):
    username: str
    password: str

class GrowattPlantSyncRequest(BaseModel):
    username: str
    password: str
    plant_name: str

@api_router.post("/integrations/growatt/sync-all")
async def sync_all_growatt(current_user: dict = Depends(get_current_user)):
    """Trigger manual sync of all Growatt plants - runs synchronously."""
    from services.scheduler import sync_all_growatt_plants
    try:
        await sync_all_growatt_plants()
        return {"success": True, "message": "Sincronizacao concluida com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na sincronizacao: {str(e)}")


@api_router.post("/integrations/growatt/login")
async def growatt_login(request: GrowattLoginRequest, current_user: dict = Depends(get_current_user)):
    """Login to Growatt OSS portal and get plant list"""
    try:
        await reset_growatt_oss_service()
        service = get_growatt_oss_service()
        login_result = await service.login(request.username, request.password)
    
        if not login_result.get('success'):
            raise HTTPException(status_code=400, detail=login_result.get('error', 'Login Growatt falhou'))
    
        plants = await service.get_plants()
    
        return {
            "success": True,
            "message": "Login realizado com sucesso",
            "plants": plants,
            "total": len(plants)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Growatt login error: {e}")
        await reset_growatt_oss_service()
        raise HTTPException(status_code=500, detail=f"Erro ao conectar com Growatt: {str(e)}")

@api_router.post("/integrations/growatt/plants")
async def list_growatt_plants(request: GrowattLoginRequest, current_user: dict = Depends(get_current_user)):
    """List all plants from Growatt OSS account"""
    service = get_growatt_oss_service()
    
    # Login if not already logged in
    if not service.logged_in:
        login_result = await service.login(request.username, request.password)
        if not login_result.get('success'):
            raise HTTPException(status_code=400, detail=login_result.get('error', 'Login Growatt falhou'))
    
    # Get plants
    plants = await service.get_plants(force_refresh=True)
    
    return {
        "success": True,
        "plants": plants,
        "total": len(plants)
    }

@api_router.post("/integrations/growatt/plant-details")
async def get_growatt_plant_details(request: GrowattPlantSyncRequest, current_user: dict = Depends(get_current_user)):
    """Get detailed information for a specific Growatt plant"""
    service = get_growatt_oss_service()
    
    # Login if not already logged in
    if not service.logged_in:
        login_result = await service.login(request.username, request.password)
        if not login_result.get('success'):
            raise HTTPException(status_code=400, detail=login_result.get('error', 'Login Growatt falhou'))
    
    # Get plant details
    details = await service.get_plant_details(request.plant_name)
    
    if not details:
        raise HTTPException(status_code=404, detail=f"Usina '{request.plant_name}' não encontrada na conta Growatt")
    
    return {
        "success": True,
        "plant": details
    }

@api_router.post("/integrations/growatt/sync-plant/{plant_id}")
async def sync_growatt_plant_data(
    plant_id: str,
    request: Optional[dict] = None,
    current_user: dict = Depends(get_current_user)
):
    """Sync generation data from Growatt for a specific plant using saved or provided credentials."""
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True}, {'_id': 0})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina nao encontrada")

    # Use saved credentials or from request
    username = (request or {}).get('username') or plant.get('growatt_username') or ''
    password = (request or {}).get('password') or plant.get('growatt_password') or ''
    growatt_name = plant.get('growatt_plant_name') or plant.get('name') or ''

    if not username or not password:
        raise HTTPException(status_code=400, detail="Credenciais Growatt nao configuradas. Va em Configuracoes da usina ou Portais para conectar.")
    if not growatt_name:
        raise HTTPException(status_code=400, detail="Nome da usina Growatt nao configurado.")

    # Reset and login
    await reset_growatt_oss_service()
    service = get_growatt_oss_service()
    login_result = await service.login(username, password)
    if not login_result.get('success'):
        raise HTTPException(status_code=400, detail=login_result.get('error', 'Login Growatt falhou'))

    # Get plant info from Growatt list
    plants_list = await service.get_plants()
    plant_data = next((p for p in plants_list if p.get('name','').lower() == growatt_name.lower()), None)
    if not plant_data:
        plant_data = next((p for p in plants_list if growatt_name.lower() in p.get('name','').lower()), None)

    records_saved = 0
    today_str = today_brazil().strftime('%Y-%m-%d')
    growatt_plant_id = plant_data.get('id', '') if plant_data else ''

    # Update plant info from Growatt (capacity, installation date, status)
    update_fields = {
        'last_growatt_sync': now_brazil().isoformat(),
        'growatt_status': plant_data.get('status', 'unknown') if plant_data else 'unknown',
    }
    if plant_data:
        if plant_data.get('capacity_kwp') and plant_data['capacity_kwp'] > 0:
            update_fields['capacity_kwp'] = plant_data['capacity_kwp']
        if plant_data.get('installation_date'):
            update_fields['installation_date'] = plant_data['installation_date']
        if plant_data.get('city'):
            update_fields['city'] = plant_data['city']
        if growatt_plant_id:
            update_fields['growatt_plant_id'] = growatt_plant_id

    # Save today's generation from the list
    if plant_data and plant_data.get('today_energy_kwh', 0) > 0:
        await db.generation_data.update_one(
            {'plant_id': plant_id, 'date': today_str},
            {'$set': {'generation_kwh': plant_data['today_energy_kwh'], 'source': 'growatt'}},
            upsert=True
        )
        records_saved = 1

    # Fetch FULL HISTORY via Growatt internal API (monthly data)
    if growatt_plant_id:
        from dateutil.relativedelta import relativedelta
        install_date = plant_data.get('installation_date', '') if plant_data else ''
        # Parse install date to determine start
        start_date = None
        if install_date:
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']:
                try:
                    start_date = datetime.strptime(install_date, fmt)
                    break
                except: pass
        if not start_date:
            start_date = datetime.now() - timedelta(days=365)  # Default: last 12 months

        current = start_date.replace(day=1)
        end = datetime.now()
        
        while current <= end:
            month_str = current.strftime('%Y-%m')
            try:
                data = await service.page.evaluate(f'''
                    async () => {{
                        try {{
                            const res = await fetch('/panel/plant/getPlantData', {{
                                method: 'POST',
                                headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                                body: 'plantId={growatt_plant_id}&type=2&date={month_str}'
                            }});
                            return await res.json();
                        }} catch(e) {{ return {{error: e.toString()}}; }}
                    }}
                ''')
                
                obj = data.get('obj', {}) if data else {}
                energys = obj.get('energys', [])
                dates_list = obj.get('dates', [])
                
                if energys and dates_list:
                    for i, val in enumerate(energys):
                        if i < len(dates_list) and val:
                            try:
                                gen_kwh = float(val)
                                if gen_kwh > 0:
                                    day_date = dates_list[i]
                                    await db.generation_data.update_one(
                                        {'plant_id': plant_id, 'date': day_date},
                                        {'$set': {'generation_kwh': gen_kwh, 'source': 'growatt'}},
                                        upsert=True
                                    )
                                    records_saved += 1
                            except (ValueError, TypeError):
                                pass
            except Exception as e:
                logger.warning(f"Growatt history {month_str}: {e}")
            
            current += relativedelta(months=1)

    await db.plants.update_one({'id': plant_id}, {'$set': update_fields})

    await log_activity(plant_id, "growatt_sync",
        f"Sincronizado Growatt: {records_saved} registro(s) ({plant_data.get('status','?') if plant_data else '?'})",
        current_user.get('name'))

    await reset_growatt_oss_service()

    return {
        "success": True,
        "records_saved": records_saved,
        "sync_data": {
            "date": today_str,
            "generation_kwh": plant_data.get('today_energy_kwh', 0) if plant_data else 0,
            "status": plant_data.get('status', 'unknown') if plant_data else 'unknown',
            "capacity_kwp": plant_data.get('capacity_kwp', 0) if plant_data else 0,
            "installation_date": plant_data.get('installation_date', '') if plant_data else '',
        },
        "message": f"Sincronizado: {records_saved} registros de geracao importados",
    }


@api_router.get("/integrations/growatt/hourly/{plant_id}")
async def get_growatt_hourly(
    plant_id: str,
    date: str,
    current_user: dict = Depends(get_current_user)
):
    """Get hourly generation data from Growatt for a specific date."""
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True}, {'_id': 0})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina nao encontrada")

    username = plant.get('growatt_username') or ''
    password = plant.get('growatt_password') or ''
    growatt_name = plant.get('growatt_plant_name') or plant.get('name') or ''

    if not username or not password:
        raise HTTPException(status_code=400, detail="Credenciais Growatt nao configuradas. Va em Configuracoes.")

    await reset_growatt_oss_service()
    service = get_growatt_oss_service()
    login_result = await service.login(username, password)
    if not login_result.get('success'):
        raise HTTPException(status_code=400, detail="Login Growatt falhou")

    result = await service.get_plant_hourly_data(growatt_name, date)
    await reset_growatt_oss_service()
    return result


@api_router.post("/integrations/growatt/download-range/{plant_id}")
async def download_growatt_range(
    plant_id: str,
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Download and save generation data from Growatt for a date range."""
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True}, {'_id': 0})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina nao encontrada")

    username = plant.get('growatt_username') or ''
    password = plant.get('growatt_password') or ''
    growatt_name = plant.get('growatt_plant_name') or plant.get('name') or ''
    start_date = request.get('start_date', '')
    end_date = request.get('end_date', '')

    if not username or not password or not growatt_name:
        raise HTTPException(status_code=400, detail="Credenciais Growatt nao configuradas")
    if not start_date or not end_date:
        raise HTTPException(status_code=400, detail="Datas obrigatorias")

    # Use Playwright web scraping (API is blocked)
    await reset_growatt_oss_service()
    service = get_growatt_oss_service()
    login_result = await service.login(username, password)
    if not login_result.get('success'):
        raise HTTPException(status_code=400, detail="Login Growatt falhou: " + login_result.get('error', 'Unknown error'))

    records_saved = 0
    
    # Get all plants from Growatt to find the correct one with plantId
    plants = await service.get_plants()
    target_plant = None
    for p in plants:
        if growatt_name.lower() in p.get('name', '').lower():
            target_plant = p
            break
    
    if not target_plant:
        raise HTTPException(status_code=404, detail=f"Usina '{growatt_name}' não encontrada no Growatt")
    
    logger.info(f"Found plant: {target_plant.get('name')} - today_energy_kwh: {target_plant.get('today_energy_kwh')}")
    
    # For now, we can only get TODAY's data reliably
    # The historical data API requires the real plantId which is hard to obtain via scraping
    today_str = today_brazil().strftime('%Y-%m-%d')
    daily_gen = target_plant.get('today_energy_kwh', 0)
    
    if daily_gen and daily_gen > 0:
        existing = await db.generation_data.find_one({'plant_id': plant_id, 'date': today_str})
        if existing:
            await db.generation_data.update_one(
                {'plant_id': plant_id, 'date': today_str},
                {'$set': {'generation_kwh': daily_gen, 'source': 'growatt', 'updated_at': now_brazil().isoformat()}}
            )
        else:
            await db.generation_data.insert_one({
                'id': str(uuid.uuid4()), 'plant_id': plant_id,
                'date': today_str, 'generation_kwh': daily_gen,
                'source': 'growatt', 'created_at': now_brazil().isoformat()
            })
        records_saved += 1
        logger.info(f"Saved today's data: {today_str} = {daily_gen} kWh")
    
    # Note: Historical data download is limited due to Growatt API restrictions
    # The system will sync daily data automatically via the scheduler

    await db.plants.update_one({'id': plant_id}, {'$set': {
        'last_growatt_sync': now_brazil().isoformat(),
    }})

    await log_activity(plant_id, "growatt_download",
        f"Download Growatt: {start_date} a {end_date} ({records_saved} registros)",
        current_user.get('name'))
    
    await reset_growatt_oss_service()

    return {
        "success": True,
        "records_saved": records_saved,
        "start_date": start_date,
        "end_date": end_date,
        "message": f"{records_saved} registro(s) do dia atual importado(s). Nota: O download de histórico está limitado devido a restrições da API Growatt. O sistema sincroniza automaticamente os dados diários.",
    }

@api_router.get("/integrations/growatt/import-history/{plant_id}")
async def get_import_history(plant_id: str, current_user: dict = Depends(get_current_user)):
    """Get import history for a plant from activity log."""
    # Get activities related to growatt downloads from activity_logs collection
    activities = await db.activity_logs.find(
        {'plant_id': plant_id, 'action': {'$in': [
            'growatt_download', 'growatt_sync', 'sync_growatt', 
            'growatt_excel_upload', 'imported_from_growatt'
        ]}},
        {'_id': 0}
    ).sort('created_at', -1).limit(20).to_list(20)
    
    history = []
    for act in activities:
        # Parse the description to extract date range
        description = act.get('description', '')
        interval = ''
        # Try to extract date range
        if ' a ' in description:
            # Format: "Download Growatt: 2025-08-18 a 2026-02-23 (10 registros)"
            parts = description.split(':')
            if len(parts) > 1:
                date_part = parts[1].strip()
                if '(' in date_part:
                    interval = date_part.split('(')[0].strip()
                else:
                    interval = date_part
        
        history.append({
            'id': act.get('id', ''),
            'timestamp': act.get('created_at', ''),
            'interval': interval or description[:50],
            'details': description,
            'user': act.get('user_name', ''),
            'status': 'success',  # If it's in the log, it was successful
        })
    
    return history


@api_router.get("/integrations/growatt/power-curve/{plant_id}")
async def get_growatt_power_curve(
    plant_id: str,
    date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch real-time power curve data from Growatt OSS portal.
    This gets the actual power readings from all inverters combined.
    """
    import math
    
    if not date:
        date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True}, {'_id': 0})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina nao encontrada")
    
    username = plant.get('growatt_username') or ''
    password = plant.get('growatt_password') or ''
    growatt_name = plant.get('growatt_plant_name') or plant.get('name') or ''
    growatt_plant_id = plant.get('growatt_plant_id') or ''
    
    if not username or not password:
        return {"success": False, "error": "Credenciais Growatt não configuradas", "curve": []}
    
    try:
        await reset_growatt_oss_service()
        service = get_growatt_oss_service()
        login_result = await service.login(username, password)
        
        if not login_result.get('success'):
            return {"success": False, "error": "Falha no login Growatt", "curve": []}
        
        # Get real plantId if we don't have it
        if not growatt_plant_id:
            plants_list = await service.get_plants()
            for p in plants_list:
                if growatt_name.lower() in p.get('name', '').lower():
                    growatt_plant_id = p.get('plant_id') or p.get('id', '')
                    # Update plant with real ID
                    if growatt_plant_id:
                        await db.plants.update_one({'id': plant_id}, {'$set': {'growatt_plant_id': growatt_plant_id}})
                    break
        
        if not growatt_plant_id:
            return {"success": False, "error": "ID da usina Growatt não encontrado", "curve": []}
        
        # Fetch power data using Growatt's internal API
        # type=0 = power (instant), type=1 = energy (daily)
        power_data = await service.page.evaluate(f'''
            async () => {{
                try {{
                    // Try getPlantPower endpoint (gives power over time)
                    const res = await fetch('/panel/plant/getPlantData', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                        body: 'plantId={growatt_plant_id}&type=0&date={date}'
                    }});
                    return await res.json();
                }} catch(e) {{
                    return {{error: e.toString()}};
                }}
            }}
        ''')
        
        await reset_growatt_oss_service()
        
        # Parse the response
        curve_points = []
        total_kwh = 0
        peak_kw = 0
        
        if power_data and not power_data.get('error'):
            obj = power_data.get('obj', {})
            powers = obj.get('powers', [])  # Power in W at each interval
            times = obj.get('times', [])    # Time strings
            
            if powers and times:
                for i, (time_str, power_w) in enumerate(zip(times, powers)):
                    try:
                        power_kw = float(power_w) / 1000 if power_w else 0
                        curve_points.append({
                            'time': time_str,
                            'power_kw': round(power_kw, 2)
                        })
                        if power_kw > peak_kw:
                            peak_kw = power_kw
                    except (ValueError, TypeError):
                        pass
            
            # Get energy data too
            energys = obj.get('energys', [])
            if energys:
                try:
                    total_kwh = sum(float(e) for e in energys if e)
                except:
                    pass
        
        # Calculate performance
        prognosis = plant.get('monthly_prognosis_kwh', 0)
        daily_prognosis = prognosis / 30 if prognosis > 0 else 0
        performance = (total_kwh / daily_prognosis * 100) if daily_prognosis > 0 and total_kwh > 0 else 0
        
        return {
            "success": True,
            "plant_name": plant.get('name', ''),
            "date": date,
            "capacity_kwp": plant.get('capacity_kwp', 0),
            "total_kwh": round(total_kwh, 2),
            "peak_kw": round(peak_kw, 2),
            "performance": round(performance, 1),
            "status": plant.get('growatt_status') or plant.get('status', 'unknown'),
            "curve": curve_points,
            "source": "growatt_api"
        }
        
    except Exception as e:
        logger.error(f"Error fetching Growatt power curve: {e}")
        return {"success": False, "error": str(e), "curve": []}


# Keep old endpoint for backward compatibility
@api_router.post("/integrations/growatt/sync")
async def sync_growatt_data(request: GrowattPlantSyncRequest, current_user: dict = Depends(get_current_user)):
    """Sync generation data from Growatt for a specific plant"""
    service = get_growatt_oss_service()
    
    # Login if not already logged in
    if not service.logged_in:
        login_result = await service.login(request.username, request.password)
        if not login_result.get('success'):
            raise HTTPException(status_code=400, detail=login_result.get('error', 'Login Growatt falhou'))
    
    # Get sync data
    sync_result = await service.sync_plant_energy_data(request.plant_name)
    
    if not sync_result.get('success'):
        raise HTTPException(status_code=400, detail=sync_result.get('error', 'Falha ao sincronizar dados'))
    
    # Save to database - find local plant that matches by name
    local_plant = await db.plants.find_one({
        '$or': [
            {'name': {'$regex': request.plant_name, '$options': 'i'}},
            {'growatt_plant_name': request.plant_name}
        ],
        'is_active': True
    })
    
    records_saved = 0
    if local_plant and sync_result.get('data'):
        data = sync_result['data']
        if data.get('date') and data.get('generation_kwh', 0) > 0:
            await db.generation_data.update_one(
                {'plant_id': local_plant['id'], 'date': data['date']},
                {'$set': {
                    'generation_kwh': data['generation_kwh'],
                    'source': 'growatt',
                    'synced_at': datetime.now(timezone.utc).isoformat()
                }},
                upsert=True
            )
            records_saved = 1
        
        # Log activity
        await log_activity(local_plant['id'], "growatt_sync", 
                          f"Sincronização Growatt: {data.get('generation_kwh', 0)} kWh importados para {data.get('date')}", 
                          current_user.get('name'))
    
    return {
        "success": True,
        "plant_name": request.plant_name,
        "data": sync_result.get('data'),
        "records_saved": records_saved,
        "local_plant_found": local_plant is not None,
        "message": f"Sincronização concluída. Dados salvos para {sync_result.get('data', {}).get('date')}." if local_plant else "Dados obtidos, mas nenhuma usina local vinculada encontrada."
    }

@api_router.post("/integrations/growatt/logout")
async def growatt_logout(current_user: dict = Depends(get_current_user)):
    """Logout from Growatt OSS portal and cleanup resources"""
    await reset_growatt_oss_service()
    return {"success": True, "message": "Logout realizado com sucesso"}

@api_router.post("/integrations/growatt/link-plant")
async def link_growatt_plant(
    plant_id: str,
    growatt_plant_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Link a local plant to a Growatt plant by name"""
    result = await db.plants.update_one(
        {'id': plant_id, 'is_active': True},
        {'$set': {
            'growatt_plant_name': growatt_plant_name,
            'inverter_integration': 'growatt'
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    
    return {
        "success": True,
        "message": f"Usina vinculada à Growatt: {growatt_plant_name}"
    }

# ==================== PORTAL - IMPORT PLANTS ====================

@api_router.post("/portals/growatt/import-plants")
async def import_growatt_plants(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Import selected Growatt plants into the system."""
    username = request.get('username', '')
    password = request.get('password', '')
    selected_plants = request.get('plants', [])  # list of {name, capacity_kwp, city, growatt_id}
    client_id = request.get('client_id', '')

    if not selected_plants:
        raise HTTPException(status_code=400, detail="Nenhuma usina selecionada")

    # Verify client exists if provided
    if client_id:
        client = await db.clients.find_one({'id': client_id, 'is_active': True})
        if not client:
            raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    imported = []
    skipped = []

    for gp in selected_plants:
        # Check if already exists by name
        existing = await db.plants.find_one({
            'name': {'$regex': f'^{gp["name"]}$', '$options': 'i'},
            'is_active': True
        })
        if existing:
            # Update existing with Growatt credentials if missing
            update_fields = {
                'growatt_username': username,
                'growatt_password': password,
                'growatt_plant_name': gp.get('name', ''),
                'growatt_plant_id': gp.get('growatt_id', ''),
                'inverter_integration': 'growatt',
                'growatt_status': gp.get('status', 'unknown'),
            }
            if gp.get('capacity_kwp') and not existing.get('capacity_kwp'):
                update_fields['capacity_kwp'] = float(gp.get('capacity_kwp', 0))
            if gp.get('city') and not existing.get('city'):
                update_fields['city'] = gp.get('city', '')
            if gp.get('installation_date') and not existing.get('installation_date'):
                update_fields['installation_date'] = gp.get('installation_date', '')
            await db.plants.update_one({'id': existing['id']}, {'$set': update_fields})
            skipped.append(gp['name'])
            continue

        plant = Plant(
            name=gp.get('name', ''),
            client_id=client_id or '',
            capacity_kwp=float(gp.get('capacity_kwp', 0)),
            city=gp.get('city', ''),
            inverter_brand='growatt',
        )
        doc = plant.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['growatt_plant_name'] = gp.get('name', '')
        doc['growatt_plant_id'] = gp.get('growatt_id', '')
        doc['growatt_username'] = username
        doc['growatt_password'] = password
        doc['inverter_integration'] = 'growatt'
        doc['growatt_status'] = gp.get('status', 'unknown')
        doc['installation_date'] = gp.get('installation_date', '')
        doc['total_energy_kwh'] = gp.get('total_energy_kwh', 0)
        doc['device_count'] = gp.get('device_count', 0)
        await db.plants.insert_one(doc)
        imported.append(gp['name'])

        # Auto-calculate prognosis from city irradiance
        await auto_calculate_prognosis(plant.id, gp.get('city', ''), float(gp.get('capacity_kwp', 0)))

        await log_activity(plant.id, "imported_from_growatt",
            f"Usina importada da Growatt: {gp['name']} ({gp.get('capacity_kwp',0)} kWp)",
            current_user.get('name'))

    return {
        "success": True,
        "imported": imported,
        "skipped": skipped,
        "total_imported": len(imported),
        "total_skipped": len(skipped),
    }

# ==================== GROWATT API (LIGHTWEIGHT) ====================

from services.growatt_api_service import GrowattAPIService, GROWATT_AVAILABLE

@api_router.post("/integrations/growatt-api/login")
async def growatt_api_login(request: GrowattLoginRequest, current_user: dict = Depends(get_current_user)):
    """Login to Growatt using API library (fast, no browser)."""
    if not GROWATT_AVAILABLE:
        raise HTTPException(status_code=503, detail="growattServer nao instalado")
    svc = GrowattAPIService()
    result = svc.login(request.username, request.password)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Login falhou'))
    plants = svc.get_plants()
    return {"success": True, "user": result.get('user'), "plants": plants, "total": len(plants)}


@api_router.post("/integrations/growatt-api/sync-plant")
async def growatt_api_sync_plant(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Sync generation data from Growatt API for a specific plant and month."""
    if not GROWATT_AVAILABLE:
        raise HTTPException(status_code=503, detail="growattServer nao instalado")

    username = request.get('username', '')
    password = request.get('password', '')
    growatt_plant_id = request.get('growatt_plant_id', '')
    plant_id = request.get('plant_id', '')
    year = int(request.get('year', datetime.now().year))
    month = int(request.get('month', datetime.now().month))

    if not all([username, password, growatt_plant_id, plant_id]):
        raise HTTPException(status_code=400, detail="Campos obrigatorios: username, password, growatt_plant_id, plant_id")

    # Verify local plant exists
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina nao encontrada")

    svc = GrowattAPIService()
    login_result = svc.login(username, password)
    if not login_result.get('success'):
        raise HTTPException(status_code=400, detail=login_result.get('error'))

    # Get overview
    overview = svc.get_overview(growatt_plant_id)

    # Sync daily data for the month
    daily_data = svc.sync_generation_data(growatt_plant_id, year, month)

    inserted = 0
    updated = 0
    for d in daily_data:
        existing = await db.generation_data.find_one({'plant_id': plant_id, 'date': d['date']})
        if existing:
            await db.generation_data.update_one(
                {'plant_id': plant_id, 'date': d['date']},
                {'$set': {'generation_kwh': d['generation_kwh'], 'source': 'growatt_api'}}
            )
            updated += 1
        else:
            doc = {
                'id': str(uuid.uuid4()),
                'plant_id': plant_id,
                'date': d['date'],
                'generation_kwh': d['generation_kwh'],
                'source': 'growatt_api',
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            await db.generation_data.insert_one(doc)
            inserted += 1

    # Update plant with growatt info
    await db.plants.update_one(
        {'id': plant_id},
        {'$set': {
            'growatt_plant_id': growatt_plant_id,
            'inverter_integration': 'growatt',
            'last_growatt_sync': datetime.now(timezone.utc).isoformat(),
            'growatt_status': overview.get('status', 'unknown'),
        }}
    )

    # Log activity
    await log_activity(plant_id, "growatt_sync",
        f"Sincronizado Growatt API: {year}-{month:02d} ({inserted} novos, {updated} atualizados)",
        current_user.get('name'))

    return {
        "success": True,
        "inserted": inserted,
        "updated": updated,
        "total_processed": inserted + updated,
        "overview": overview,
        "month": f"{year}-{month:02d}",
    }


@api_router.post("/integrations/growatt-api/save-credentials")
async def growatt_save_credentials(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Save Growatt credentials for a plant (encrypted)."""
    plant_id = request.get('plant_id', '')
    username = request.get('username', '')
    password = request.get('password', '')
    growatt_plant_id = request.get('growatt_plant_id', '')

    plant = await db.plants.find_one({'id': plant_id, 'is_active': True})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina nao encontrada")

    await db.plants.update_one(
        {'id': plant_id},
        {'$set': {
            'growatt_username': username,
            'growatt_password': password,  # In production, encrypt this
            'growatt_plant_id': growatt_plant_id,
            'inverter_integration': 'growatt',
        }}
    )

    return {"success": True, "message": "Credenciais salvas"}


# ==================== GROWATT EXCEL UPLOAD ====================

from services.growatt_excel_service import parse_growatt_excel, extract_generation_records

@api_router.post("/generation-data/upload-growatt-excel/{plant_id}")
async def upload_growatt_excel(
    plant_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a Growatt Excel report and extract generation data.
    The Excel file should be the monthly report exported from Growatt portal.
    """
    # Verify plant exists
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    
    # Validate file type
    if not file.filename.lower().endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Apenas arquivos Excel (.xls, .xlsx) são aceitos")
    
    # Read and parse file
    content = await file.read()
    parsed_data = parse_growatt_excel(content, file.filename)
    
    if not parsed_data.get('success'):
        return {
            "success": False,
            "error": parsed_data.get('error', 'Erro ao processar arquivo Excel'),
            "filename": file.filename
        }
    
    # Extract generation records
    records = extract_generation_records(parsed_data, plant_id)
    
    # Insert/update records
    records_inserted = 0
    records_updated = 0
    
    for record in records:
        existing = await db.generation_data.find_one({
            'plant_id': record['plant_id'],
            'date': record['date']
        })
        
        if existing:
            await db.generation_data.update_one(
                {'plant_id': record['plant_id'], 'date': record['date']},
                {'$set': {'generation_kwh': record['generation_kwh'], 'source': record['source']}}
            )
            records_updated += 1
        else:
            gen_data = GenerationData(**record)
            doc = gen_data.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.generation_data.insert_one(doc)
            records_inserted += 1
    
    # Log activity
    await log_activity(
        plant_id,
        "growatt_excel_upload",
        f"Importado Excel Growatt: {parsed_data.get('plant_name', file.filename)} - {parsed_data.get('month_year', '')}",
        current_user.get('name'),
        {'total_kwh': parsed_data.get('total_generation_kwh', 0), 'inverters': len(parsed_data.get('inverters', []))}
    )
    
    return {
        "success": True,
        "message": "Excel Growatt processado com sucesso",
        "filename": file.filename,
        "parsed_data": {
            "plant_name": parsed_data.get('plant_name'),
            "month_year": parsed_data.get('month_year'),
            "total_generation_kwh": parsed_data.get('total_generation_kwh'),
            "inverters_count": len(parsed_data.get('inverters', [])),
            "days_with_data": len(parsed_data.get('daily_generation', []))
        },
        "records_inserted": records_inserted,
        "records_updated": records_updated,
        "total_processed": records_inserted + records_updated
    }

# ==================== PDF REPORT GENERATION ====================

from services.pdf_generator_service import generate_plant_report
from fastapi.responses import Response
import calendar

@api_router.get("/reports/download-pdf/{plant_id}")
async def download_pdf_report(
    plant_id: str,
    month: str,
    report_type: str = "basic",
    current_user: dict = Depends(get_current_user)
):
    """
    Generate and download a PDF report for a plant.
    
    Args:
        plant_id: Plant ID
        month: Month in YYYY-MM format
        report_type: 'basic' or 'complete'
    """
    # Get plant
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True}, {'_id': 0})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    
    # Get client
    client = await db.clients.find_one({'id': plant.get('client_id')}, {'_id': 0})
    
    # Parse month
    try:
        year, mon = map(int, month.split('-'))
        days_in_month = calendar.monthrange(year, mon)[1]
        start_date = f"{month}-01"
        end_date = f"{month}-{days_in_month:02d}"
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de mês inválido. Use YYYY-MM")
    
    # Get generation data
    gen_data = await db.generation_data.find({
        'plant_id': plant_id,
        'date': {'$gte': start_date, '$lte': end_date}
    }, {'_id': 0}).sort('date', 1).to_list(100)
    
    total_generation = sum(d.get('generation_kwh', 0) for d in gen_data)
    prognosis = plant.get('monthly_prognosis_kwh') or 0
    
    # Calculate month-specific prognosis from irradiance if city is set
    kwp = plant.get('capacity_kwp', 0)
    city_name = plant.get('city', '')
    if city_name and kwp:
        city_doc = await db.irradiance_cities.find_one(
            {'city': {'$regex': f'^{city_name}$', '$options': 'i'}}, {'_id': 0}
        )
        if city_doc:
            months_key = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
            irr_val = city_doc.get('irradiance', {}).get(months_key[mon - 1], 0)
            irr_prog = round(kwp * days_in_month * ((irr_val / 1000) - 0.1) * 0.75, 2)
            if irr_prog > 0:
                prognosis = irr_prog
    
    # Build daily generation list (fill gaps with 0)
    daily_dict = {d['date']: d['generation_kwh'] for d in gen_data}
    daily_generation = []
    for day in range(1, days_in_month + 1):
        date_str = f"{month}-{day:02d}"
        daily_generation.append({
            'day': day,
            'date': date_str,
            'generation_kwh': daily_dict.get(date_str, 0)
        })
    
    # Get historical data (last 4 months) - need UC IDs for invoice lookup
    units = await db.consumer_units.find({'plant_id': plant_id, 'is_active': True}, {'_id': 0}).to_list(100)
    unit_ids = [u['id'] for u in units]
    uc_numbers = [u.get('uc_number','') for u in units if u.get('uc_number')]
    all_matching_ucs = await db.consumer_units.find(
        {'uc_number': {'$in': uc_numbers}}, {'_id': 0, 'id': 1}
    ).to_list(500)
    all_uc_ids = list(set(unit_ids + [u['id'] for u in all_matching_ucs]))

    historical = []
    for i in range(1, 5):  # Last 4 months
        hist_date = datetime(year, mon, 1) - timedelta(days=30*i)
        hist_month = hist_date.strftime('%Y-%m')
        hist_start = f"{hist_month}-01"
        hist_days = calendar.monthrange(hist_date.year, hist_date.month)[1]
        hist_end = f"{hist_month}-{hist_days:02d}"
        
        hist_gen = await db.generation_data.find({
            'plant_id': plant_id,
            'date': {'$gte': hist_start, '$lte': hist_end}
        }, {'_id': 0, 'generation_kwh': 1}).to_list(100)
        
        hist_total = sum(d['generation_kwh'] for d in hist_gen)
        
        # Get invoices for this historical month
        hist_ref = f"{hist_date.month:02d}/{hist_date.year}"
        hist_invoices = await db.invoices.find({
            '$or': [
                {'consumer_unit_id': {'$in': all_uc_ids}, 'reference_month': hist_ref},
                {'plant_id': plant_id, 'reference_month': hist_ref},
            ]
        }, {'_id': 0}).to_list(1000)
        # Deduplicate historical invoices by uc_number+reference_month
        h_seen_uc_ref = set()
        h_unique = []
        for hi in hist_invoices:
            uc_num = hi.get('uc_number', '')
            if not uc_num:
                cu_id = hi.get('consumer_unit_id', '')
                cu_doc = next((u for u in units if u['id'] == cu_id), None)
                if cu_doc:
                    uc_num = cu_doc.get('uc_number', '')
                else:
                    cu_doc_db = await db.consumer_units.find_one({'id': cu_id}, {'_id': 0, 'uc_number': 1})
                    uc_num = cu_doc_db.get('uc_number', '') if cu_doc_db else ''
            dedup_key = f"{uc_num}_{hist_ref}"
            if dedup_key in h_seen_uc_ref and uc_num:
                continue
            if uc_num:
                h_seen_uc_ref.add(dedup_key)
            h_unique.append(hi)
        
        # Get Consumo PT from generator UC only (Grupo A)
        hist_cons_p = 0
        for hi in h_unique:
            if hi.get('tariff_group') == 'A' or hi.get('is_generator'):
                hist_cons_p += hi.get('energy_registered_p_kwh', 0) or 0
        hist_cons_fp = sum(hi.get('energy_registered_fp_kwh', 0) or 0 for hi in h_unique)
        hist_eco = sum(hi.get('amount_saved_brl', 0) or 0 for hi in h_unique)
        hist_fat = sum(hi.get('amount_total_brl', 0) or 0 for hi in h_unique)
        
        # Format month as MMM/YYYY
        month_abbr = {1: 'JAN', 2: 'FEV', 3: 'MAR', 4: 'ABR', 5: 'MAI', 6: 'JUN',
                      7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OUT', 11: 'NOV', 12: 'DEZ'}
        
        historical.append({
            'month': f"{month_abbr[hist_date.month]}./{hist_date.year}",
            'month_year': hist_month,
            'generation_kwh': round(hist_total, 2),
            'prognosis_kwh': prognosis,
            'consumption_p': round(hist_cons_p, 0),
            'consumption_fp': round(hist_cons_fp, 0),
            'economizado': round(hist_eco, 2),
            'faturado': round(hist_fat, 2),
        })
    
    # Calculate environmental impact (last 12 months)
    twelve_months_ago = (datetime(year, mon, 1) - timedelta(days=365)).strftime('%Y-%m-%d')
    all_gen = await db.generation_data.find({
        'plant_id': plant_id,
        'date': {'$gte': twelve_months_ago}
    }, {'_id': 0, 'generation_kwh': 1}).to_list(10000)
    total_gen_12m = sum(d['generation_kwh'] for d in all_gen)
    co2_avoided = total_gen_12m * 0.5  # kg
    trees_saved = co2_avoided / 22  # trees/year
    
    # Prepare report data
    report_data = {
        'plant_name': plant.get('name', 'Usina FV'),
        'company_name': client.get('name', 'ON Soluções Energéticas') if client else 'ON Soluções Energéticas',
        'month_year': month,
        'capacity_kwp': plant.get('capacity_kwp', 0),
        'total_generation_kwh': total_generation,
        'prognosis_kwh': prognosis,
        'prognosis_annual_kwh': plant.get('annual_prognosis_kwh', prognosis * 12),
        'daily_generation': daily_generation,
        'historical': historical,
        'environmental': {
            'co2_avoided_kg': co2_avoided,
            'trees_saved': trees_saved
        },
        # Include logo URL (plant logo or client logo)
        'logo_url': plant.get('logo_url') or (client.get('logo_url') if client else None)
    }
    
    # Always include financial and consumer data (unified report)
    # (units, unit_ids, all_uc_ids already defined above for historical)
    
    # Get invoices for the month - match by reference_month (MM/YYYY format)
    ref_month = f"{mon:02d}/{year}"

    invoices = await db.invoices.find({
        '$or': [
            {'consumer_unit_id': {'$in': all_uc_ids}, 'reference_month': ref_month},
            {'plant_id': plant_id, 'reference_month': ref_month},
        ]
    }, {'_id': 0}).to_list(1000)
    
    # Deduplicate by invoice id AND by uc_number+reference_month
    seen = set()
    seen_uc_ref = set()
    unique_invoices = []
    for inv in invoices:
        iid = inv.get('id')
        if iid in seen:
            continue
        seen.add(iid)
        # Also deduplicate by UC number + reference month
        uc_num = inv.get('uc_number', '')
        if not uc_num:
            # Find UC number from consumer_unit_id
            cu_id = inv.get('consumer_unit_id', '')
            cu_doc = next((u for u in units if u['id'] == cu_id), None)
            if not cu_doc:
                cu_doc_db = await db.consumer_units.find_one({'id': cu_id}, {'_id': 0, 'uc_number': 1})
                uc_num = cu_doc_db.get('uc_number', '') if cu_doc_db else ''
            else:
                uc_num = cu_doc.get('uc_number', '')
        ref = inv.get('reference_month', '')
        uc_ref_key = f"{uc_num}_{ref}"
        if uc_ref_key in seen_uc_ref and uc_num:
            continue  # Skip duplicate UC+month
        if uc_num:
            seen_uc_ref.add(uc_ref_key)
        unique_invoices.append(inv)
    invoices = unique_invoices
    
    total_saved = sum(i.get('amount_saved_brl', 0) for i in invoices)
    total_billed = sum(i.get('amount_total_brl', 0) for i in invoices)
    
    # Get all-time savings for ROI - deduplicate by uc_number+reference_month
    all_invoices = await db.invoices.find({
        '$or': [
            {'consumer_unit_id': {'$in': all_uc_ids}},
            {'plant_id': plant_id},
        ]
    }, {'_id': 0, 'amount_saved_brl': 1, 'id': 1, 'consumer_unit_id': 1, 'reference_month': 1, 'uc_number': 1}).to_list(10000)
    seen_all_uc_ref = set()
    total_savings_all_time = 0
    for inv in all_invoices:
        # Resolve uc_number
        uc_num = inv.get('uc_number', '')
        if not uc_num:
            cu_id = inv.get('consumer_unit_id', '')
            cu_doc = next((u for u in units if u['id'] == cu_id), None)
            if cu_doc:
                uc_num = cu_doc.get('uc_number', '')
            else:
                cu_doc_db = await db.consumer_units.find_one({'id': cu_id}, {'_id': 0, 'uc_number': 1})
                uc_num = cu_doc_db.get('uc_number', '') if cu_doc_db else ''
        ref = inv.get('reference_month', '')
        dedup_key = f"{uc_num}_{ref}"
        if dedup_key in seen_all_uc_ref and uc_num:
            continue
        if uc_num:
            seen_all_uc_ref.add(dedup_key)
        total_savings_all_time += inv.get('amount_saved_brl', 0) or 0
    
    total_investment = plant.get('total_investment') or 0
    roi_monthly = (total_saved / total_investment * 100) if total_investment > 0 else 0
    roi_total = (total_savings_all_time / total_investment * 100) if total_investment > 0 else 0
    
    report_data['financial'] = {
        'saved_brl': total_saved,
        'billed_brl': total_billed,
        'roi_monthly': roi_monthly,
        'roi_total': roi_total,
        'total_savings': total_savings_all_time
    }
    
    # Energy flow from GENERATOR UC invoice only (not sum of all)
    generator_inv = None
    for inv in invoices:
        uc = next((u for u in units if u['id'] == inv.get('consumer_unit_id') and u.get('is_generator')), None)
        if not uc:
            inv_cu_id = inv.get('consumer_unit_id', '')
            inv_uc_doc = await db.consumer_units.find_one({'id': inv_cu_id}, {'_id': 0, 'uc_number': 1})
            if inv_uc_doc:
                uc = next((u for u in units if u.get('uc_number') == inv_uc_doc.get('uc_number') and u.get('is_generator')), None)
        if uc:
            generator_inv = inv
            break

    if generator_inv:
        report_data['energy_injected_p'] = generator_inv.get('energy_injected_p_kwh', 0) or 0
        report_data['energy_injected_fp'] = generator_inv.get('energy_injected_fp_kwh', 0) or 0
        report_data['consumption_p'] = generator_inv.get('energy_registered_p_kwh', 0) or 0
        report_data['consumption_fp'] = generator_inv.get('energy_registered_fp_kwh', 0) or 0
    else:
        report_data['energy_injected_p'] = 0
        report_data['energy_injected_fp'] = 0
        report_data['consumption_p'] = 0
        report_data['consumption_fp'] = 0
    
    # Consumer units with invoice data - deduplicate by uc_number
    consumer_units_data = []
    seen_ucs = set()
    for inv in invoices:
        # Find matching UC in THIS plant
        unit = next((u for u in units if u['id'] == inv.get('consumer_unit_id')), None)
        if not unit:
            # Match by uc_number from the UC that the invoice belongs to
            inv_cu_id = inv.get('consumer_unit_id', '')
            inv_uc_doc = await db.consumer_units.find_one({'id': inv_cu_id}, {'_id': 0, 'uc_number': 1})
            if inv_uc_doc:
                inv_uc_num = inv_uc_doc.get('uc_number', '')
                unit = next((u for u in units if u.get('uc_number') == inv_uc_num), None)
        if not unit:
            continue
        uc_num = unit.get('uc_number', '')
        if uc_num in seen_ucs:
            continue
        seen_ucs.add(uc_num)
        consumer_units_data.append({
            'uc_number': unit.get('uc_number', ''),
            'name': unit.get('holder_name') or unit.get('address') or '',
            'cycle': f"{(inv.get('billing_cycle_start') or '')[:10]} a {(inv.get('billing_cycle_end') or '')[:10]}",
            'percentage': unit.get('compensation_percentage', 0),
            'consumption_registered': (inv.get('energy_registered_fp_kwh', 0) or 0) + (inv.get('energy_registered_p_kwh', 0) or 0),
            'energy_compensated': (inv.get('energy_compensated_fp_kwh', 0) or 0) + (inv.get('energy_compensated_p_kwh', 0) or 0),
            'energy_billed': inv.get('energy_billed_fp_kwh', 0) or 0,
            'credit_previous': inv.get('credits_balance_fp_kwh', 0) or 0,
            'credit_accumulated': inv.get('credits_accumulated_fp_kwh', 0) or 0,
            'amount_billed': inv.get('amount_total_brl', 0) or 0,
            'amount_saved': inv.get('amount_saved_brl', 0) or 0,
        })
    
    report_data['consumer_units'] = consumer_units_data
    
    # Generate PDF
    try:
        pdf_bytes = generate_plant_report(report_data, report_type)
    except Exception as e:
        import traceback
        logger.error(f"Error generating PDF: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")
    
    # Return PDF
    filename = f"relatorio_{plant.get('name', 'usina').replace(' ', '_')}_{month}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

# Include the router in the main app
app.include_router(api_router)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
