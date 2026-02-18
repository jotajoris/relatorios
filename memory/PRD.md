# PRD - Sistema de Gerenciamento de Usinas Solares

## Visão Geral
Sistema web para gerenciamento de usinas de energia solar fotovoltaica, com foco na gestão de unidades consumidoras (UCs) e faturas de energia da COPEL.

## Stack Tecnológica
- **Frontend:** React + Vite + TailwindCSS + shadcn/ui
- **Backend:** FastAPI + Python
- **Database:** MongoDB
- **Autenticação:** JWT

## Funcionalidades Implementadas

### ✅ Autenticação
- Login com email/senha
- JWT com tokens de acesso e refresh
- Proteção de rotas

### ✅ Gestão de Clientes
- CRUD completo
- Associação com usinas

### ✅ Gestão de Usinas
- CRUD completo
- Dados: capacidade, localização, inversor, prognóstico mensal/anual
- Associação com clientes

### ✅ Gestão de Unidades Consumidoras (UCs) - **ATUALIZADO 18/02/2026**
- CRUD completo com novos campos:
  - `uc_number`: Número da UC na COPEL
  - `tariff_group`: Grupo tarifário (A ou B)
  - `tariff_modality`: Modalidade tarifária (Convencional, Horária Verde/Azul)
  - `is_generator`: Indica se é UC geradora
  - `compensation_percentage`: % de compensação para UCs beneficiárias
  - `generator_uc_ids`: IDs das UCs geradoras que abastecem esta UC
  - `contracted_demand_kw`: Demanda contratada (Grupo A)
- Interface com badges visuais:
  - Geradora (amarelo) / Beneficiária (azul)
  - Grupo A (roxo) / Grupo B (verde)
  - % de compensação

### ✅ Upload de Faturas PDF - **NOVO 18/02/2026**
- Upload manual de PDFs de faturas COPEL
- Parser automático que extrai:
  - Dados financeiros (valor total, economizado)
  - Dados de energia (registrada, injetada, compensada)
  - Créditos acumulados (Ponta e Fora Ponta)
  - Demanda (Grupo A)
  - Tributos (ICMS, Iluminação Pública)
- Suporte a Grupo A e Grupo B
- Interface para edição/validação antes de salvar

### ✅ Integração COPEL - **PARCIAL**
- Login automático no portal COPEL ✅
- Listagem de UCs da conta ✅
- Seleção de UC ✅
- **Limitação:** reCAPTCHA pode bloquear automação em alguns casos

### ⚠️ Integração Growatt - **PENDENTE**
- Serviço implementado com suporte a múltiplos servidores
- Credenciais fornecidas não funcionam ("User Does Not Exist")
- Necessário verificar servidor correto para conta brasileira

### ⚠️ Geração de PDF - **PLACEHOLDER**
- Endpoint criado mas não implementado
- Decisão pendente: usar `pyppeteer` ou microsserviço Node.js

## Estrutura de Dados

### ConsumerUnit (UC)
```json
{
  "id": "uuid",
  "plant_id": "uuid",
  "uc_number": "113577680",
  "address": "Rua...",
  "city": "Curitiba",
  "state": "PR",
  "tariff_group": "A" | "B",
  "tariff_modality": "Convencional" | "Horária Verde" | "Horária Azul",
  "is_generator": true | false,
  "compensation_percentage": 100.0,
  "contracted_demand_kw": 50.0,
  "generator_uc_ids": ["uuid1", "uuid2"]
}
```

### InvoiceData (Fatura)
```json
{
  "id": "uuid",
  "consumer_unit_id": "uuid",
  "plant_id": "uuid",
  "reference_month": "02/2026",
  "billing_cycle_start": "31/12/2025",
  "billing_cycle_end": "31/01/2026",
  "due_date": "01/03/2026",
  "amount_total_brl": 3291.95,
  "amount_saved_brl": 500.00,
  "energy_registered_fp_kwh": 212.0,
  "energy_injected_fp_kwh": 150.0,
  "energy_compensated_fp_kwh": 100.0,
  "credits_accumulated_fp_kwh": 50.0,
  "tariff_group": "A",
  "is_generator": true,
  "source": "upload" | "copel_api" | "manual"
}
```

## Endpoints API

### Autenticação
- `POST /api/auth/login` - Login
- `POST /api/auth/token` - Token de acesso

### UCs
- `GET /api/consumer-units` - Listar UCs
- `POST /api/consumer-units` - Criar UC
- `PUT /api/consumer-units/{id}` - Atualizar UC
- `DELETE /api/consumer-units/{id}` - Remover UC

### Faturas
- `GET /api/invoices` - Listar faturas
- `POST /api/invoices/upload-pdf/{uc_id}` - Upload de PDF
- `POST /api/invoices/save-from-upload` - Salvar fatura após edição

### Integrações
- `POST /api/integrations/copel/test-login` - Testar login COPEL
- `POST /api/integrations/copel/list-ucs` - Listar UCs da conta COPEL
- `POST /api/integrations/growatt/test-login` - Testar login Growatt

## Tarefas Pendentes

### P0 - Alta Prioridade
1. ~~Implementar upload de PDF de faturas~~ ✅
2. ~~Atualizar modelo de UCs com campos de compensação~~ ✅
3. Resolver problema de credenciais Growatt

### P1 - Média Prioridade
1. Implementar geração de relatórios PDF
2. Criar página de listagem/histórico de faturas
3. Resolver problema de CAPTCHA da COPEL (usar serviço de terceiros ou aceitar limitação)

### P2 - Baixa Prioridade
1. Job agendado para sincronização automática de dados
2. Integrar outras marcas de inversores (Solis, Fronius)
3. Sistema de notificações de performance
4. Finalizar CI/CD (aguarda credenciais FTP)

## Credenciais de Teste
- **App:** projetos.onsolucoes@gmail.com / on123456
- **COPEL:** 77952604000162 / Portao62*
- **Growatt:** BTAVB001 / Comercial2023 (não funciona - verificar servidor)

## Preview URL
https://copel-sync.preview.emergentagent.com
