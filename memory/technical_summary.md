# Resumo Técnico - ON Soluções Energéticas (Solar Management System)

**Data de geração:** Dezembro/2025  
**Domínio de produção:** https://onusinas.com  
**Ambiente de preview:** https://solar-report-1.preview.emergentagent.com

---

## 1. Stack Tecnológica

### 1.1 Frontend
| Componente | Versão | Descrição |
|------------|--------|-----------|
| **React** | 19.0.0 | Framework UI principal |
| **Vite/CRA** | via craco | Build tooling (Create React App com customização) |
| **TailwindCSS** | 3.4.17 | Framework CSS utilitário |
| **shadcn/ui** | - | Biblioteca de componentes (Radix UI) |
| **Recharts** | 3.6.0 | Gráficos e visualizações |
| **React Router** | 7.5.1 | Roteamento SPA |
| **Axios** | 1.8.4 | Cliente HTTP |
| **react-image-crop** | 11.0.10 | Recorte de imagens (logos) |
| **date-fns** | 4.1.0 | Manipulação de datas |
| **Lucide React** | 0.507.0 | Biblioteca de ícones |
| **Zod** | 3.24.4 | Validação de schemas |

### 1.2 Backend
| Componente | Versão | Descrição |
|------------|--------|-----------|
| **Python** | 3.x | Linguagem principal |
| **FastAPI** | 0.110.1 | Framework web assíncrono |
| **Uvicorn** | 0.25.0 | Servidor ASGI |
| **Motor** | 3.3.1 | Driver assíncrono MongoDB |
| **Pydantic** | 2.12.5 | Validação e serialização de dados |
| **PyJWT** | 2.11.0 | Autenticação JWT |
| **bcrypt** | 4.1.3 | Hash de senhas |
| **Playwright** | 1.58.0 | Automação web (scraping) |
| **APScheduler** | 3.11.2 | Agendador de tarefas |
| **ReportLab** | 4.4.10 | Geração de PDFs |
| **Pandas** | 3.0.1 | Processamento de dados |
| **Cloudinary** | 1.44.1 | SDK para upload de imagens |
| **pdfplumber** | 0.11.9 | Parsing de PDFs |
| **requests** | 2.32.5 | Cliente HTTP síncrono |
| **openpyxl** | 3.1.5 | Leitura/escrita de Excel |

### 1.3 Banco de Dados
| Componente | Versão | Descrição |
|------------|--------|-----------|
| **MongoDB** | - | Banco de dados NoSQL |
| **Motor** | 3.3.1 | Driver assíncrono para Python |

---

## 2. Estrutura do Banco de Dados (MongoDB)

### 2.1 Collections Principais

#### `users`
```javascript
{
  id: String (UUID),
  email: String,
  name: String,
  password: String (bcrypt hash),
  role: String ("admin"),
  is_active: Boolean,
  created_at: DateTime
}
```

#### `clients`
```javascript
{
  id: String (UUID),
  name: String,
  email: String,
  phone: String,
  document: String (CPF/CNPJ),
  address: String,
  city: String,
  state: String,
  logo_url: String (Cloudinary URL),
  contact_person: String,
  is_active: Boolean,
  created_at: DateTime
}
```

#### `plants` (Usinas)
```javascript
{
  id: String (UUID),
  name: String,
  client_id: String (FK),
  utility_id: String (FK - concessionária),
  capacity_kwp: Float,
  installation_date: String,
  address: String,
  city: String,
  state: String ("PR"),
  latitude: Float,
  longitude: Float,
  inverter_brand: String,
  monthly_prognosis_kwh: Float,
  annual_prognosis_kwh: Float,
  total_investment: Float,
  logo_url: String,
  efficiency_loss_year1: Float (2.5%),
  efficiency_loss_year2: Float (1.5%),
  efficiency_loss_other: Float (0.5%),
  is_monitored: Boolean,
  
  // Credenciais Growatt
  growatt_username: String,
  growatt_password: String,
  growatt_plant_name: String,
  growatt_plant_id: String,
  growatt_status: String,
  last_growatt_sync: DateTime,
  
  // Credenciais COPEL
  copel_cnpj: String,
  copel_password: String,
  
  is_active: Boolean,
  status: String ("online"),
  created_at: DateTime
}
```

#### `consumer_units` (Unidades Consumidoras)
```javascript
{
  id: String (UUID),
  plant_id: String (FK),
  uc_number: String (ex: "113577680"),
  contract_number: String,
  address: String,
  city: String,
  state: String,
  holder_name: String,
  holder_document: String (CPF/CNPJ),
  is_generator: Boolean,
  compensation_percentage: Float (0-100),
  tariff_group: String ("A" ou "B"),
  tariff_modality: String,
  contracted_demand_kw: Float (Grupo A),
  generator_uc_ids: Array<String>,
  is_active: Boolean,
  created_at: DateTime
}
```

#### `invoices` (Faturas)
```javascript
{
  id: String (UUID),
  consumer_unit_id: String (FK),
  plant_id: String (FK),
  reference_month: String ("MM/YYYY"),
  billing_cycle_start: String,
  billing_cycle_end: String,
  due_date: String,
  
  // Valores financeiros
  amount_total_brl: Float,
  amount_saved_brl: Float,
  
  // Energia Fora Ponta
  energy_registered_fp_kwh: Float,
  energy_billed_fp_kwh: Float,
  energy_injected_fp_kwh: Float,
  energy_compensated_fp_kwh: Float,
  credits_accumulated_fp_kwh: Float,
  
  // Energia Ponta (Grupo A)
  energy_registered_p_kwh: Float,
  energy_billed_p_kwh: Float,
  energy_injected_p_kwh: Float,
  energy_compensated_p_kwh: Float,
  credits_accumulated_p_kwh: Float,
  
  // Demanda (Grupo A)
  demand_registered_kw: Float,
  demand_contracted_kw: Float,
  demand_billed_kw: Float,
  
  // Créditos
  credits_balance_p_kwh: Float,
  credits_balance_fp_kwh: Float,
  
  // Tributos
  public_lighting_brl: Float,
  icms_brl: Float,
  pis_cofins_brl: Float,
  
  tariff_group: String,
  is_generator: Boolean,
  pdf_file_path: String,
  source: String ("manual", "copel_api", "upload", "copel_auto"),
  created_at: DateTime
}
```

#### `generation_data` (Dados de Geração)
```javascript
{
  id: String (UUID),
  plant_id: String (FK),
  date: String ("YYYY-MM-DD"),
  generation_kwh: Float,
  source: String ("manual", "growatt_auto", "excel"),
  created_at: DateTime
}
```

#### `utilities` (Concessionárias)
```javascript
{
  id: String (UUID),
  name: String (ex: "COPEL", "Celesc"),
  code: String,
  state: String,
  is_active: Boolean,
  created_at: DateTime
}
```

#### `client_logins` (Credenciais de Portais)
```javascript
{
  id: String (UUID),
  inverter_app: String ("Growatt", "FusionSolar", etc),
  on_unit: String ("ON CWB", "ON CG"),
  client_name: String,
  login: String,
  password: String,
  site_url: String,
  is_installer: Boolean,
  created_at: DateTime
}
```

#### `portal_connections` (Conexões de Portais)
```javascript
{
  id: String (UUID),
  portal_id: String ("growatt", "huawei", "deye"),
  username: String,
  password: String,
  connected: Boolean,
  last_connected: String,
  created_at: DateTime
}
```

#### `invoice_download_statuses` (Status de Downloads)
```javascript
{
  id: String (UUID),
  plant_id: String (FK),
  consumer_unit_id: String (FK),
  uc_number: String,
  year: Int,
  month: Int (1-12),
  status: String ("pending", "success", "unavailable", "error"),
  error_message: String,
  invoice_id: String,
  attempted_at: DateTime,
  created_at: DateTime
}
```

#### `monthly_reports` (Relatórios Mensais)
```javascript
{
  id: String (UUID),
  plant_id: String (FK),
  reference_month: String ("MM/YYYY"),
  year: Int,
  month: Int,
  performance_percentage: Float,
  total_generation_kwh: Float,
  prognosis_kwh: Float,
  status: String ("pending", "generated", "sent"),
  pdf_url: String,
  notes: String,
  created_at: DateTime,
  generated_at: DateTime
}
```

#### `app_settings` (Configurações)
```javascript
{
  key: String ("growatt_sync_interval"),
  value: Any,
  updated_at: String
}
```

---

## 3. Hospedagem Atual

### 3.1 Ambiente de Preview/Desenvolvimento
- **Plataforma:** Emergent Agent Platform
- **URL:** https://solar-report-1.preview.emergentagent.com
- **Arquitetura:** Container Kubernetes
- **Serviços:**
  - Frontend: Porta 3000 (CRA/React)
  - Backend: Porta 8001 (FastAPI/Uvicorn)
  - MongoDB: localhost:27017
- **Gerenciamento:** Supervisor (supervisorctl)

### 3.2 Configuração de Produção
- **Domínio:** https://onusinas.com
- **CORS configurado para:**
  - https://onusinas.com
  - https://www.onusinas.com
  - https://energy-hub-24.emergent.host

### 3.3 Variáveis de Ambiente

**Backend (.env):**
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
CORS_ORIGINS=https://onusinas.com,...
CLOUDINARY_CLOUD_NAME=ddlinjhhw
CLOUDINARY_API_KEY=851693648935782
CLOUDINARY_API_SECRET=***
JWT_SECRET=***
```

**Frontend (.env):**
```
REACT_APP_BACKEND_URL=https://solar-report-1.preview.emergentagent.com
WDS_SOCKET_PORT=443
```

---

## 4. Integrações Externas

### 4.1 Growatt OSS Portal (Web Scraping)
- **URL:** https://oss.growatt.com
- **Método:** Playwright (headless Chromium)
- **Serviço:** `/backend/services/growatt_service.py`
- **Funcionalidades:**
  - Login automatizado
  - Listagem de usinas
  - Coleta de dados de geração diária
  - Extração de status (online/offline/warning)
  - Coleta de energia hoje/mês/total
- **Fluxo:**
  1. Abre navegador headless
  2. Navega para página de login
  3. Fecha modais (região, termos)
  4. Preenche credenciais
  5. Aguarda redirecionamento para /index
  6. Extrai dados das tabelas de plantas

### 4.2 COPEL AVA Portal (Web Scraping)
- **URL:** https://www.copel.com/avaweb/
- **Método:** Playwright (headless Chromium)
- **Serviço:** `/backend/services/copel_ava_service.py`
- **Funcionalidades:**
  - Login com CNPJ/senha
  - Listagem de UCs disponíveis
  - Download de faturas em PDF
  - Parsing automático de faturas
- **Timeout:** 120 segundos (configurável)
- **Fluxo:**
  1. Login no portal AVA
  2. Navega para "Segunda Via de Fatura"
  3. Seleciona UC
  4. Lista faturas disponíveis
  5. Download do PDF
  6. Parsing com pdfplumber

### 4.3 Cloudinary (Upload de Imagens)
- **Serviço:** `/backend/services/cloudinary_service.py`
- **Funcionalidades:**
  - Upload de logos de clientes
  - Upload de logos de usinas
  - Transformações de imagem (resize, crop)
- **Configuração:**
  - Cloud Name: ddlinjhhw
  - Folder: solar-management/

### 4.4 Solarman (Em desenvolvimento - BLOQUEADO)
- **URL:** https://pro.solarmanpv.com
- **Status:** Bloqueado por CAPTCHA Cloudflare
- **Serviço:** `/backend/services/solarman_service.py`
- **Aguardando:** Credenciais da API oficial

---

## 5. Processos em Background (Jobs/Schedulers)

### 5.1 APScheduler Configuration
- **Serviço:** `/backend/services/scheduler.py`
- **Tipo:** AsyncIOScheduler

### 5.2 Jobs Agendados

#### Download Automático de Faturas COPEL
- **ID:** `download_invoices`
- **Trigger:** CronTrigger (03:00 UTC = 00:00 BRT)
- **Frequência:** Diário à meia-noite (horário de Brasília)
- **Função:** `download_missing_invoices()`
- **Comportamento:**
  1. Busca usinas com credenciais COPEL configuradas
  2. Verifica faturas faltantes dos últimos 3 meses
  3. Para cada usina:
     - Login no portal COPEL
     - Download das faturas pendentes
     - Parsing automático do PDF
     - Inserção no banco de dados
  4. Log de resultados

#### Sincronização Automática Growatt
- **ID:** `sync_growatt_interval`
- **Trigger:** IntervalTrigger
- **Frequência:** Configurável (padrão: 30 minutos)
- **Função:** `sync_all_growatt_plants()`
- **Configuração dinâmica:** Via collection `app_settings`
- **Comportamento:**
  1. Busca todas as usinas ativas
  2. Agrupa por credenciais de login
  3. Para cada grupo:
     - Login no portal Growatt
     - Extrai dados de todas as usinas
     - Atualiza `generation_data` com energia do dia
     - Atualiza status da usina (online/offline)
     - Salva `growatt_plant_id` se disponível

### 5.3 Jobs On-Demand (Background Tasks)

#### Download Individual de Fatura
- **Endpoint:** `POST /api/integrations/copel/download-single-invoice`
- **Execução:** BackgroundTasks do FastAPI
- **Rastreamento:** Collection `invoice_download_statuses`

#### Download em Lote de Faturas
- **Endpoint:** `POST /api/integrations/copel/download-all-invoices`
- **Execução:** BackgroundTasks do FastAPI
- **Parâmetros:** year, month
- **Rastreamento:** Job ID único para polling

---

## 6. Arquitetura de Arquivos

```
/app/
├── backend/
│   ├── server.py              # API principal (~5100 linhas)
│   ├── requirements.txt       # Dependências Python
│   ├── .env                   # Variáveis de ambiente
│   ├── assets/
│   │   └── logo_on.png        # Logo da empresa
│   ├── services/
│   │   ├── growatt_service.py      # Integração Growatt (Playwright)
│   │   ├── growatt_api_service.py  # Tentativa API Growatt
│   │   ├── growatt_excel_service.py # Import Excel Growatt
│   │   ├── copel_service.py        # Integração COPEL (simplificada)
│   │   ├── copel_ava_service.py    # Integração COPEL AVA (Playwright)
│   │   ├── solarman_service.py     # Integração Solarman (bloqueada)
│   │   ├── cloudinary_service.py   # Upload de imagens
│   │   ├── pdf_generator_service.py # Geração de relatórios PDF
│   │   ├── pdf_parser_service.py   # Parsing de faturas PDF
│   │   └── scheduler.py            # Jobs agendados (APScheduler)
│   └── tests/
│       └── ...
├── frontend/
│   ├── src/
│   │   ├── App.js             # Roteamento principal
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx  # Dashboard principal
│   │   │   ├── Plants.jsx     # Lista de usinas
│   │   │   ├── PlantDetail.jsx # Detalhes da usina
│   │   │   ├── Clients.jsx    # Gestão de clientes
│   │   │   ├── ConsumerUnits.jsx # Gestão de UCs
│   │   │   ├── Invoices.jsx   # Gestão de faturas
│   │   │   ├── Reports.jsx    # Relatórios mensais
│   │   │   ├── Portais.jsx    # Conexões com portais
│   │   │   ├── Settings.jsx   # Configurações
│   │   │   ├── Profile.jsx    # Perfil do usuário
│   │   │   └── Login.jsx      # Autenticação
│   │   ├── components/
│   │   │   ├── Layout.jsx     # Layout principal
│   │   │   ├── KPICard.jsx    # Cards de métricas
│   │   │   ├── StatusBadge.jsx # Badges de status
│   │   │   ├── ImageCropper.jsx # Recorte de imagens
│   │   │   └── ui/            # Componentes shadcn/ui
│   │   ├── contexts/
│   │   │   └── AuthContext.js # Context de autenticação
│   │   └── services/
│   │       └── api.js         # Cliente Axios
│   ├── package.json
│   └── tailwind.config.js
└── memory/
    └── PRD.md                 # Documento de requisitos
```

---

## 7. Endpoints da API (Principais)

### 7.1 Autenticação
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/auth/register` | Registro de usuário |
| POST | `/api/auth/login` | Login (JWT) |
| POST | `/api/auth/refresh` | Refresh token |
| GET | `/api/auth/me` | Dados do usuário atual |

### 7.2 CRUD Principal
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET/POST | `/api/clients` | Listar/Criar clientes |
| GET/PUT/DELETE | `/api/clients/{id}` | CRUD cliente |
| GET/POST | `/api/plants` | Listar/Criar usinas |
| GET/PUT/DELETE | `/api/plants/{id}` | CRUD usina |
| GET/POST | `/api/consumer-units` | Listar/Criar UCs |
| GET/POST | `/api/invoices` | Listar/Criar faturas |
| GET/POST | `/api/utilities` | Listar/Criar concessionárias |

### 7.3 Dashboard e Relatórios
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/dashboard/summary` | Resumo geral |
| GET | `/api/dashboard/power-curve/{plant_id}` | Curva de potência |
| POST | `/api/reports/generate/{plant_id}` | Gerar relatório PDF |
| GET | `/api/reports/list` | Listar relatórios |

### 7.4 Integrações
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/integrations/growatt/connect` | Conectar Growatt |
| POST | `/api/integrations/growatt/sync/{plant_id}` | Sincronizar usina |
| POST | `/api/integrations/copel/connect` | Conectar COPEL |
| POST | `/api/integrations/copel/download-invoice` | Download fatura |
| POST | `/api/integrations/copel/download-all-invoices` | Download em lote |
| POST | `/api/integrations/copel/download-single-invoice` | Download individual |
| GET | `/api/integrations/copel/download-job/{job_id}` | Status do job |

### 7.5 Upload
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/upload/logo` | Upload logo (Cloudinary) |
| POST | `/api/upload/invoice-pdf` | Upload fatura PDF |
| POST | `/api/upload/generation-excel` | Upload dados Excel |

---

## 8. Considerações para Migração

### 8.1 Dependências Críticas
1. **MongoDB:** Requer instância MongoDB acessível
2. **Playwright:** Requer instalação de browsers (`playwright install chromium`)
3. **Cloudinary:** Credenciais configuradas
4. **Supervisor:** Gerenciamento de processos (ou equivalente)

### 8.2 Portas Utilizadas
- Frontend: 3000
- Backend: 8001
- MongoDB: 27017

### 8.3 Browsers do Playwright
- Caminho: `/pw-browsers`
- Instalação: `npx playwright install chromium`

### 8.4 Volumes/Persistência
- Banco de dados MongoDB (crítico)
- Logs do supervisor
- Cache de browsers do Playwright

### 8.5 Variáveis de Ambiente Obrigatórias
```bash
# Backend
MONGO_URL=mongodb://...
DB_NAME=...
JWT_SECRET=...
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
CORS_ORIGINS=...

# Frontend
REACT_APP_BACKEND_URL=https://...
```

### 8.6 Cron/Scheduler
- O APScheduler roda dentro do processo Python
- Jobs configurados no startup (`start_scheduler()`)
- Alternativa: Cron externo chamando endpoints da API

---

## 9. Issues Conhecidas

1. **Gráfico de Curva de Potência:** Ainda usa dados simulados (não conectado à API Growatt)
2. **Solarman:** Bloqueado por CAPTCHA, aguardando API oficial
3. **Playwright em produção:** Pode falhar se browsers não estiverem instalados
4. **server.py:** Arquivo muito grande (~5100 linhas), necessita refatoração

---

**Documento gerado automaticamente para avaliação de migração de servidor.**
