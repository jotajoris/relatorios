from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import pandas as pd
from io import BytesIO

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'solar-energy-secret-key-2025')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24
JWT_REFRESH_EXPIRATION_DAYS = 7

# Security
security = HTTPBearer()

# Create the main app
app = FastAPI(title="ON Soluções Energéticas - Solar Management API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    document: Optional[str] = None  # CPF/CNPJ
    address: Optional[str] = None
    logo_url: Optional[str] = None

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

class PlantCreate(PlantBase):
    pass

class Plant(PlantBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    status: str = "online"

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

@app.on_event("startup")
async def startup_event():
    await seed_users()

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
    await db.invoices.insert_one(doc)
    
    return {
        "success": True,
        "message": "Fatura salva com sucesso",
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
    
    summaries = []
    for plant in plants:
        # Get generation for this month
        gen_data = await db.generation_data.find({
            'plant_id': plant['id'],
            'date': {'$gte': month_start}
        }, {'_id': 0, 'generation_kwh': 1}).to_list(100)
        
        total_gen = sum(d.get('generation_kwh', 0) for d in gen_data)
        prognosis = plant.get('monthly_prognosis_kwh') or 0
        performance = (total_gen / prognosis * 100) if prognosis and prognosis > 0 else 0
        
        # Get client name
        client = await db.clients.find_one({'id': plant['client_id']}, {'_id': 0, 'name': 1})
        
        summaries.append({
            'id': plant['id'],
            'name': plant['name'],
            'client_name': client.get('name', 'N/A') if client else 'N/A',
            'capacity_kwp': plant.get('capacity_kwp', 0),
            'status': plant.get('status', 'online'),
            'generation_kwh': round(total_gen, 2),
            'prognosis_kwh': prognosis,
            'performance': round(performance, 1)
        })
    
    return summaries

@api_router.get("/dashboard/generation-chart/{plant_id}")
async def get_generation_chart(
    plant_id: str,
    month: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    if not month:
        month = datetime.now(timezone.utc).strftime('%Y-%m')
    
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
    plant = await db.plants.find_one({'id': plant_id}, {'_id': 0, 'monthly_prognosis_kwh': 1})
    daily_prognosis = (plant.get('monthly_prognosis_kwh', 0) / days_in_month) if plant else 0
    
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
    
    return chart_data

# ==================== INVERTER CREDENTIALS ====================

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
    prognosis = plant.get('monthly_prognosis_kwh', 0)
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

# ==================== GROWATT INTEGRATION ====================

from services.growatt_service import get_growatt_service, GrowattService
from services.copel_service import CopelService, test_copel_login, download_copel_invoice

class GrowattLoginRequest(BaseModel):
    plant_id: str  # Our internal plant ID
    username: str
    password: str

class GrowattSyncRequest(BaseModel):
    plant_id: str
    growatt_plant_id: str
    days: int = 30

@api_router.post("/integrations/growatt/test-login")
async def test_growatt_login(request: GrowattLoginRequest, current_user: dict = Depends(get_current_user)):
    """Test Growatt credentials and list available plants"""
    service = GrowattService()
    result = service.login(request.username, request.password)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Login failed'))
    
    # Get plant list
    plants = service.get_plant_list()
    
    return {
        "success": True,
        "user_name": result.get('user_name'),
        "plants": plants
    }

@api_router.post("/integrations/growatt/sync")
async def sync_growatt_data(request: GrowattSyncRequest, current_user: dict = Depends(get_current_user)):
    """Sync generation data from Growatt for a plant"""
    
    # Get stored credentials
    cred = await db.inverter_credentials.find_one({
        'plant_id': request.plant_id,
        'brand': 'growatt',
        'is_active': True
    })
    
    if not cred:
        raise HTTPException(status_code=404, detail="Credenciais Growatt não encontradas para esta usina")
    
    # Login to Growatt
    service = GrowattService()
    
    # Note: In production, password should be decrypted
    # For now, we'll need the user to provide credentials
    raise HTTPException(
        status_code=501, 
        detail="Sincronização automática em desenvolvimento. Use o teste de login primeiro."
    )

@api_router.get("/integrations/growatt/plants/{plant_id}")
async def get_growatt_plant_details(plant_id: str, current_user: dict = Depends(get_current_user)):
    """Get details of a Growatt plant (requires active session)"""
    service = get_growatt_service()
    
    if not service.logged_in:
        raise HTTPException(status_code=401, detail="Faça login no Growatt primeiro")
    
    details = service.get_plant_details(plant_id)
    if not details:
        raise HTTPException(status_code=404, detail="Usina não encontrada no Growatt")
    
    return details

@api_router.post("/integrations/growatt/fetch-data")
async def fetch_and_save_growatt_data(
    plant_id: str,
    growatt_plant_id: str,
    username: str,
    password: str,
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Fetch data from Growatt and save to database"""
    
    # Verify our plant exists
    plant = await db.plants.find_one({'id': plant_id, 'is_active': True})
    if not plant:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    
    # Login to Growatt
    service = GrowattService()
    login_result = service.login(username, password)
    
    if not login_result.get('success'):
        raise HTTPException(status_code=400, detail=login_result.get('error', 'Login failed'))
    
    # Sync data
    sync_result = service.sync_plant_data(growatt_plant_id, days)
    
    if not sync_result.get('success'):
        raise HTTPException(status_code=500, detail=sync_result.get('error', 'Sync failed'))
    
    # Save to database
    records_inserted = 0
    records_updated = 0
    
    for record in sync_result.get('data', []):
        date_str = record.get('date')
        gen_kwh = record.get('generation_kwh', 0)
        
        if not date_str or gen_kwh <= 0:
            continue
        
        existing = await db.generation_data.find_one({'plant_id': plant_id, 'date': date_str})
        if existing:
            await db.generation_data.update_one(
                {'plant_id': plant_id, 'date': date_str},
                {'$set': {'generation_kwh': gen_kwh, 'source': 'growatt'}}
            )
            records_updated += 1
        else:
            data = GenerationData(plant_id=plant_id, date=date_str, generation_kwh=gen_kwh, source='growatt')
            doc = data.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.generation_data.insert_one(doc)
            records_inserted += 1
    
    # Update last sync time
    await db.inverter_credentials.update_one(
        {'plant_id': plant_id, 'brand': 'growatt'},
        {'$set': {'last_sync': datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "success": True,
        "records_inserted": records_inserted,
        "records_updated": records_updated,
        "total_synced": records_inserted + records_updated
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

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
