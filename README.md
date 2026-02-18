# ON Soluções Energéticas - Sistema de Gestão de Usinas Solares

Sistema completo para gestão e relatórios de usinas solares fotovoltaicas.

## Stack Tecnológico

- **Frontend**: React 19 + TailwindCSS + Shadcn/UI + Recharts
- **Backend**: FastAPI + MongoDB
- **Autenticação**: JWT com refresh tokens
- **Deploy**: GitHub Actions + Hostinger (FTP/SSH)

## Funcionalidades

### Gestão de Usinas
- ✅ Cadastro de clientes e usinas
- ✅ Cadastro de unidades consumidoras (UCs)
- ✅ Upload de dados de geração (Excel/CSV)
- ✅ Dashboard com KPIs em tempo real
- ✅ Gráficos de geração diária e histórica

### Integrações (Em desenvolvimento)
- 🔄 API Growatt - Sincronização automática
- 🔄 Portal COPEL - Download de faturas
- 🔄 Outras marcas: FusionSolar, Sungrow, Deye, SAJ, SolarMan

### Relatórios
- ✅ Relatório mensal por usina
- ✅ KPIs: Geração, Desempenho, Economia, ROI
- ✅ Dados da concessionária (COPEL)
- ✅ Impacto ambiental (CO₂, árvores)
- 🔄 Exportação para PDF

## Instalação Local

### Pré-requisitos
- Node.js 18+
- Python 3.10+
- MongoDB

### Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas configurações

# Iniciar servidor
uvicorn server:app --reload --port 8001
```

### Frontend

```bash
cd frontend

# Instalar dependências
yarn install

# Configurar variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com a URL do backend

# Iniciar servidor de desenvolvimento
yarn start
```

## Variáveis de Ambiente

### Backend (.env)

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=solar_management
JWT_SECRET=sua-chave-secreta-muito-segura
CORS_ORIGINS=http://localhost:3000,https://seudominio.com
```

### Frontend (.env)

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

## Deploy para Hostinger

### 1. Configurar GitHub Actions

Adicione as seguintes secrets no seu repositório GitHub (Settings > Secrets > Actions):

| Secret | Descrição |
|--------|-----------|
| `FTP_HOST` | Servidor FTP da Hostinger |
| `FTP_USERNAME` | Usuário FTP |
| `FTP_PASSWORD` | Senha FTP |
| `FTP_SERVER_DIR` | Diretório no servidor (ex: `/public_html/`) |
| `REACT_APP_BACKEND_URL` | URL da API em produção |

### 2. Deploy Automático

O deploy é feito automaticamente quando você faz push na branch `main`:

```bash
git add .
git commit -m "Deploy para produção"
git push origin main
```

## Estrutura do Projeto

```
/
├── backend/
│   ├── server.py          # API FastAPI
│   ├── requirements.txt   # Dependências Python
│   └── .env              # Variáveis de ambiente
│
├── frontend/
│   ├── src/
│   │   ├── components/   # Componentes reutilizáveis
│   │   ├── pages/        # Páginas da aplicação
│   │   ├── contexts/     # Contextos React (Auth)
│   │   └── services/     # Serviços (API client)
│   ├── package.json
│   └── .env
│
├── .github/
│   └── workflows/
│       └── deploy.yml    # CI/CD Pipeline
│
└── README.md
```

## API Endpoints

### Autenticação
- `POST /api/auth/register` - Cadastrar usuário
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Renovar token
- `GET /api/auth/me` - Dados do usuário logado

### Clientes
- `GET /api/clients` - Listar clientes
- `POST /api/clients` - Criar cliente
- `PUT /api/clients/{id}` - Atualizar cliente
- `DELETE /api/clients/{id}` - Remover cliente

### Usinas
- `GET /api/plants` - Listar usinas
- `POST /api/plants` - Criar usina
- `GET /api/plants/{id}` - Detalhes da usina
- `PUT /api/plants/{id}` - Atualizar usina
- `DELETE /api/plants/{id}` - Remover usina

### Dados de Geração
- `GET /api/generation-data` - Listar dados
- `POST /api/generation-data` - Criar registro
- `POST /api/generation-data/upload/{plant_id}` - Upload Excel/CSV

### Dashboard
- `GET /api/dashboard/stats` - Estatísticas gerais
- `GET /api/dashboard/plants-summary` - Resumo das usinas

### Relatórios
- `GET /api/reports/plant/{id}` - Dados do relatório

## Cores da Marca

- **Amarelo Principal**: `#FFD600`
- **Amarelo Hover**: `#EAB308`
- **Preto**: `#1A1A1A`
- **Fundo**: `#F4F4F5`

## Suporte

Para dúvidas ou suporte, entre em contato com ON Soluções Energéticas.

## Licença

Proprietário - ON Soluções Energéticas LTDA
