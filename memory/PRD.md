# PRD - Sistema de Gerenciamento de Usinas Solares

## Visão Geral
Sistema web para gerenciamento de usinas de energia solar fotovoltaica, com foco na gestão de unidades consumidoras (UCs), faturas de energia da COPEL e relatórios de desempenho.

## Stack Tecnológica
- **Frontend:** React + Vite + TailwindCSS + shadcn/ui + Recharts
- **Backend:** FastAPI + Python
- **Database:** MongoDB
- **Autenticação:** JWT

---

## ✅ Funcionalidades Implementadas

### Autenticação
- Login com email/senha
- JWT com tokens de acesso e refresh
- Proteção de rotas

### Gestão de Clientes
- CRUD completo
- Upload de logo
- Campos: nome, email, telefone, documento, endereço, responsável

### Gestão de Usinas
- CRUD completo
- **Página de Detalhes com 4 Tabs:**

#### Tab 1: Visão Geral
- Header escuro com logo, nome, KPIs
- Gráfico de geração diária (últimos 30 dias)
- Linha de prognóstico
- Timeline de atividades recentes

#### Tab 2: Relatórios ✅ (Atualizado em 2026-02-19)
- Grid de 12 meses com cards de desempenho
- Navegação por ano
- **NOVO: Botão "Importar Excel Growatt"** - Upload de relatórios Excel exportados do portal Growatt
- **NOVO: Botão "Enviar Fatura COPEL"** - Upload manual de PDFs de faturas
- **NOVO: Botões "Básico" e "Completo"** em cada mês para download de relatórios PDF

#### Tab 3: Sistema de Crédito
- Tabela de UCs geradoras e beneficiárias
- Colunas: Denominação, Contrato, Classificação, Porcentagem, Ações
- Suporte a múltiplas geradoras
- Total de porcentagem distribuída

#### Tab 4: Configurações
- Upload de logo da usina
- Edição de cadastro (nome, potência, investimento, etc)
- Preferências (alertas, notificações)
- **Integração com Growatt** (botão "Conectar ao Growatt")

### Integração Growatt ✅
- Login no portal OSS Growatt via web scraping (Playwright)
- Listagem de todas as plantas (com paginação automática)
- Busca de detalhes de planta específica
- Sincronização de dados de geração
- Vínculo entre usina local e planta Growatt
- **50 usinas** listadas com sucesso para a conta BTAVB001
- Dialog no frontend para configuração da integração

### Upload Excel Growatt ✅ (NOVO - 2026-02-19)
- Parser inteligente para relatórios mensais exportados do Growatt
- Extração automática de dados por inversor
- Suporte a múltiplos inversores (ex: 2 inversores na usina BANANAS PORTÃO)
- Cálculo automático da geração diária combinada
- Inserção/atualização de registros no banco

### Upload Faturas COPEL ✅
- Upload manual de PDFs COPEL
- Parser automático para Grupo A e B
- Extração: valores, energia, créditos, demanda
- Interface para edição antes de salvar
- **NOVO: Modal integrado na página de detalhes da usina**

### Geração de Relatórios PDF ✅ (NOVO - 2026-02-19)
- **Relatório Básico:** 
  - KPIs gerais (Potência, Geração, Desempenho)
  - Gráfico de geração diária vs prognóstico
  - Impacto ambiental (CO2 evitado, árvores salvas)
  - Histórico de meses anteriores
- **Relatório Completo:**
  - Tudo do básico
  - Dados financeiros (Faturado, Economia, Retorno)
  - Fluxo de energia (injetada ponta/fora ponta, consumo)
  - Tabela detalhada por consumidor/contrato

### Integração COPEL
- Login automático ✅
- Listagem de UCs ✅
- Download de faturas ⚠️ (limitado por CAPTCHA)

---

## 📋 Modelo de Dados

### Plant (Usina)
```json
{
  "name": "Usina FV",
  "client_id": "uuid",
  "capacity_kwp": 365.2,
  "total_investment": 1450000,
  "monthly_prognosis_kwh": 41941,
  "annual_prognosis_kwh": 503290,
  "efficiency_loss_year1": 2.5,
  "efficiency_loss_year2": 1.5,
  "efficiency_loss_other": 0.5,
  "is_monitored": true,
  "public_share_enabled": false,
  "logo_url": "/api/logos/plant_xxx.png"
}
```

### ConsumerUnit (UC)
```json
{
  "plant_id": "uuid",
  "uc_number": "113577680",
  "address": "Rua...",
  "tariff_group": "A" | "B",
  "classification": "A4-Comercial",
  "compensation_percentage": 50.0,
  "is_generator": false,
  "generator_uc_ids": ["uuid1", "uuid2"]
}
```

### GenerationData
```json
{
  "plant_id": "uuid",
  "date": "2026-01-15",
  "generation_kwh": 1524.5,
  "source": "growatt_excel" | "growatt_api" | "manual" | "upload"
}
```

---

## 🔌 Endpoints API

### Plantas
- `GET /api/plants/{id}/full-details` - Detalhes completos com UCs, relatórios, atividades

### Upload Logo
- `POST /api/upload/logo/{type}/{id}` - Upload de logo (client/plant)
- `GET /api/logos/{filename}` - Servir arquivo de logo

### Distribuição de Créditos
- `GET /api/credit-distribution/{plant_id}` - Listar listas de distribuição
- `POST /api/credit-distribution` - Criar nova lista

### Relatórios e Geração de PDF
- `GET /api/reports/{plant_id}` - Listar relatórios
- `POST /api/reports` - Criar/atualizar relatório
- `GET /api/reports/download-pdf/{plant_id}` - **NOVO: Download PDF (básico ou completo)**

### Upload de Dados
- `POST /api/generation-data/upload-growatt-excel/{plant_id}` - **NOVO: Upload Excel Growatt**
- `POST /api/invoices/upload-pdf/{consumer_unit_id}` - Upload fatura COPEL PDF

### Integração Growatt
- `POST /api/integrations/growatt/login` - Login no portal OSS
- `POST /api/integrations/growatt/plants` - Listar usinas
- `POST /api/integrations/growatt/sync` - Sincronizar dados
- `POST /api/integrations/growatt/link-plant` - Vincular usina local

### Timeline
- `GET /api/activity/{plant_id}` - Atividades recentes
- `POST /api/activity` - Registrar atividade

---

## 🚀 Tarefas Pendentes

### P0 - Alta Prioridade
1. ~~Página de detalhes da usina com 4 tabs~~ ✅
2. ~~Sistema de distribuição de créditos~~ ✅
3. ~~Upload de logo~~ ✅
4. ~~Implementar geração de PDF de relatórios~~ ✅ (Implementado em 2026-02-19)
5. ~~Upload de Excel Growatt~~ ✅ (Implementado em 2026-02-19)

### P1 - Média Prioridade
1. ~~Integração Growatt via web scraping~~ ✅
2. Implementar CAPTCHA solver para COPEL (ou usar sessões persistentes)
3. Página de histórico de faturas com filtros
4. Personalização visual dos relatórios PDF (papel timbrado do cliente)

### P2 - Baixa Prioridade
1. Job agendado para sincronização automática (APScheduler)
2. Integrar outras marcas de inversores (Sungrow, Deye, etc)
3. Sistema de notificações (alertas de baixo desempenho)
4. CI/CD para deploy

---

## 🔐 Credenciais de Teste
- **App:** projetos.onsolucoes@gmail.com / on123456
- **Growatt (Instalador):** BTAVB001 / Comercial2023
- **COPEL:** 77952604000162 / Portao62*

## 🌐 Preview URL
https://on-usinas.preview.emergentagent.com

---

*Última atualização: 19/02/2026*
