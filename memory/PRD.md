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

#### Tab 2: Relatórios
- Grid de 12 meses com cards de desempenho
- Navegação por ano
- Botão "Gerar Relatório Personalizado" (placeholder)

#### Tab 3: Sistema de Crédito
- Tabela de UCs geradoras e beneficiárias
- Colunas: Denominação, Contrato, Classificação, Porcentagem, Ações
- Suporte a múltiplas geradoras
- Total de porcentagem distribuída

#### Tab 4: Configurações
- Upload de logo da usina
- Edição de cadastro (nome, potência, investimento, etc)
- Preferências (alertas, notificações)
- **NOVO: Integração com Growatt** (botão "Conectar ao Growatt")

### Integração Growatt ✅ (Implementado em 2026-02-18)
- Login no portal OSS Growatt via web scraping (Playwright)
- Listagem de todas as plantas (com paginação automática)
- Busca de detalhes de planta específica
- Sincronização de dados de geração
- Vínculo entre usina local e planta Growatt
- **50 usinas** listadas com sucesso para a conta BTAVB001
- Dialog no frontend para configuração da integração
- Link de compartilhamento público
- Perda de eficiência por ano

### Gestão de UCs
- CRUD completo
- Campos: número UC, endereço, cidade, estado
- Grupo tarifário (A ou B)
- Classificação (A4-Comercial, B1-Residencial, etc)
- Porcentagem de compensação
- Flag geradora/beneficiária
- Suporte a múltiplas geradoras por usina

### Upload de Faturas PDF
- Upload manual de PDFs COPEL
- Parser automático para Grupo A e B
- Extração: valores, energia, créditos, demanda
- Interface para edição antes de salvar

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

### CreditDistributionList
```json
{
  "plant_id": "uuid",
  "name": "Vigência 02/2026 - Baseada em Lista de Porcentagem",
  "effective_date": "02/2026",
  "units": [
    {"uc_number": "113577680", "percentage": 0, "is_generator": true},
    {"uc_number": "102480958", "percentage": 50, "is_generator": false}
  ]
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
- `PUT /api/credit-distribution/{id}` - Atualizar lista
- `DELETE /api/credit-distribution/{id}` - Remover lista

### Relatórios
- `GET /api/reports/{plant_id}` - Listar relatórios
- `POST /api/reports` - Criar/atualizar relatório
- `GET /api/reports/{plant_id}/years` - Anos disponíveis

### Timeline
- `GET /api/activity/{plant_id}` - Atividades recentes
- `POST /api/activity` - Registrar atividade

---

## 🚀 Tarefas Pendentes

### P0 - Alta Prioridade
1. ~~Página de detalhes da usina com 4 tabs~~ ✅
2. ~~Sistema de distribuição de créditos~~ ✅
3. ~~Upload de logo~~ ✅
4. Implementar geração de PDF de relatórios (aguardando papel timbrado)

### P1 - Média Prioridade
1. Resolver problema Growatt (credenciais não funcionam)
2. Implementar CAPTCHA solver para COPEL
3. Página de histórico de faturas

### P2 - Baixa Prioridade
1. Job agendado para sincronização automática
2. Integrar outras marcas de inversores
3. Sistema de notificações
4. CI/CD para deploy

---

## 🔐 Credenciais de Teste
- **App:** projetos.onsolucoes@gmail.com / on123456
- **COPEL:** 77952604000162 / Portao62*

## 🌐 Preview URL
https://on-usinas.preview.emergentagent.com

---

*Última atualização: 18/02/2026*
