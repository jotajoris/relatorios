# ON Soluções Energéticas - Solar Plant Management

## Problem Statement
Aplicação web full-stack para gerenciamento e elaboração de relatórios de usinas de energia solar fotovoltaica.

## Stack
- **Frontend:** React, Vite, TailwindCSS, shadcn/ui
- **Backend:** FastAPI, Python
- **Database:** MongoDB
- **Auth:** JWT (access + refresh tokens)

## Core Requirements
1. **Gerenciamento de Entidades:** CRUD para Clientes, Usinas e UCs. Upload de logo.
2. **Sistema de Créditos:** UCs geradoras e beneficiárias com distribuição de créditos.
3. **Entrada de Dados de Geração:** Upload manual de faturas PDF (COPEL, Energisa MS), planilhas Excel (Growatt), integração com inversores.
4. **Automação COPEL:** Web scraping para baixar faturas (bloqueada por reCAPTCHA).
5. **Geração de Relatórios PDF:** Relatório unificado por usina com branding ON.
6. **Página de Faturas:** Seção dedicada no menu lateral para upload de faturas.

## User Personas
- **Admin (João):** Gerencia usinas, clientes e relatórios
- **Operador:** Importa dados e monitora geração

## What's Implemented
- Auth JWT completo com seed de usuários
- CRUD de Clientes, Usinas, UCs
- Dashboard com KPIs
- Upload de Excel Growatt funcional
- **Parser de faturas COPEL (Grupo A e B) - CORRIGIDO** (19/02/2026)
- **Página de Faturas no menu lateral - IMPLEMENTADA** (19/02/2026)
- **Gerador de PDF com branding ON - CORRIGIDO** (19/02/2026)
- Sistema de Créditos (backend: distribuição percentual)
- Integração Growatt (web scraping + Excel)

## Architecture
```
/app/backend/
  server.py            # FastAPI routes
  services/
    copel_service.py         # COPEL automation (Playwright)
    pdf_parser_service.py    # Invoice PDF parser (REESCRITO)
    pdf_generator_service.py # PDF report generator (CORRIGIDO)
    growatt_service.py       # Growatt web scraping
    growatt_excel_service.py # Growatt Excel parser
  assets/
    logo_on_sem_fundo.png    # ON logo
    logo_on_fundo_preto.png  # ON logo dark
  tests/
    test_invoices_and_reports.py

/app/frontend/src/
  pages/
    Invoices.jsx       # NOVA - Página de Faturas
    PlantDetail.jsx
    Dashboard.jsx
    ...
  components/
    Layout.jsx         # ATUALIZADO - Menu com Faturas
```

## P0 - Completed
- [x] Corrigir parser de faturas PDF (copel_service.py → pdf_parser_service.py)
- [x] Criar nova página "Faturas" no menu lateral
- [x] Corrigir layout do relatório PDF
- [x] KPIs na página Relatórios: Prognóstico, Geração do Mês, Desempenho % (19/02/2026)
- [x] Formulário editável de fatura estilo SolarZ com todos os campos (19/02/2026)
- [x] Parser: Economizado = soma deduções INJETADA = 159.07 (19/02/2026)
- [x] Parser: Valor tarifa = TE + USD, Tarifa TE separada (19/02/2026)
- [x] Parser: Energia compensada Ponta = total injetada, Faturada Ponta = -265 (19/02/2026)

- [x] Cards mensais na aba Relatórios da usina: Geração, Prognóstico, Desempenho % (19/02/2026)

- [x] Parser Grupo B corrigido: UC 7 dígitos, Economizado = soma INJ OUC, Tarifa TUSD do CONSUMO (19/02/2026)

- [x] Relatório PDF unificado reescrito: Dashboard + Tabela de UCs (19/02/2026)

- [x] **Correção do Dropdown de Cidade/Estado** (23/02/2026): Adicionada normalização de estados (abreviação → nome completo) no backend e frontend. Usinas com estados como "PR", "SP" agora carregam corretamente as cidades para cálculo de prognóstico por irradiância. Alterações em:
  - `/app/backend/server.py`: Mapeamento STATE_ABBREV_MAP na API /irradiance/cities
  - `/app/frontend/src/pages/PlantDetail.jsx`: Função normalizeState() + uso nos selects
  - `/app/frontend/src/pages/Plants.jsx`: Mesma correção para o modal de edição de usinas

- [x] **Sincronização Automática Growatt** (23/02/2026): Implementado sistema completo de sincronização automática:
  - Botão "Sync Growatt" no Dashboard para sincronização manual de todas as usinas
  - Scheduler APScheduler rodando em background com intervalo configurável (padrão: 30 min)
  - Nova aba "Sincronização" em Configurações com UI para configurar intervalo
  - Status da última sincronização e próxima execução visíveis no Dashboard e Configurações
  - Alterações em:
    - `/app/backend/server.py`: Endpoints /settings/sync-interval, /settings/sync-status, /sync/growatt/all
    - `/app/backend/services/scheduler.py`: Lógica de sync automático e configuração de intervalo
    - `/app/frontend/src/pages/Settings.jsx`: Nova aba "Sincronização" com UI de configuração
    - `/app/frontend/src/pages/Dashboard.jsx`: Botão de sync manual e status

- [x] **Correção do Upload de Excel** (23/02/2026): Corrigido problema onde o seletor de arquivo não abria ao clicar em "Enviar arquivo de geração". Inputs de arquivo foram movidos para fora das abas (no topo do componente) para ficarem acessíveis globalmente.
  - Alterações em: `/app/frontend/src/pages/PlantDetail.jsx`

- [x] **Cálculo de Desempenho com Data de Instalação** (23/02/2026): O cálculo de desempenho (1D, 15D, 30D, 12M) agora considera a data de instalação da usina. Se uma usina foi instalada no dia 20 de um mês de 30 dias, o prognóstico é calculado proporcionalmente para 10 dias efetivos, não 30.
  - Exemplo: Usina instalada dia 20, gerou 1000 kWh, prognóstico mensal 3000 kWh → Desempenho = 1000 / (3000/30 * 10) = 100%
  - Alterações em: `/app/backend/server.py` - função que calcula `plants-summary`

- [x] **Salvamento do Growatt PlantId** (23/02/2026): A sincronização automática agora salva o `growatt_plant_id` real da usina no banco de dados para uso futuro.
  - Alterações em: `/app/backend/services/scheduler.py`

- [x] **Gerenciamento de Concessionárias (Utilities)** (09/03/2026): Implementado sistema completo de gerenciamento de concessionárias de energia:
  - Backend: Modelo `Utility` com campos name, code, state
  - Backend: Endpoints CRUD completos (`GET/POST/PUT/DELETE /api/utilities`)
  - Backend: Seed inicial com concessionárias principais (COPEL, Celesc, Energisa MS, CPFL Paulista, Enel SP, Cemig, Light, Coelba)
  - Backend: Campo `utility_id` adicionado ao modelo Plant para vincular usina à concessionária
  - Frontend: Seletor dropdown de concessionárias no formulário de edição da usina
  - Frontend: Botão "+" para adicionar novas concessionárias sem sair do formulário
  - Frontend: Dialog para criação de novas concessionárias
  - Alterações em:
    - `/app/backend/server.py`: Modelos Utility/UtilityBase/UtilityCreate, endpoints CRUD, seed_utilities()
    - `/app/frontend/src/pages/PlantDetail.jsx`: Estado utilities, loadUtilities(), handleCreateUtility(), seletor e dialog

- [x] **Download Automático de Faturas COPEL** (09/03/2026): Sistema completo de download em lote de faturas da Agência Virtual COPEL:
  - Backend: Modelo `InvoiceDownloadStatus` para rastrear status por UC/mês
  - Backend: Endpoint `GET /api/plants/{id}/invoice-download-status?year=YYYY` - retorna status de todas UCs
  - Backend: Endpoint `POST /api/plants/{id}/download-invoices-batch` - inicia download em lote
  - Backend: Endpoint `GET /api/download-jobs/{job_id}` - verifica progresso do job
  - Backend: Background task que processa UCs sequencialmente via Playwright/COPEL
  - Frontend: Tabela de status de faturas por UC com ícones:
    - 🕐 Relógio amarelo = Download pendente
    - ❌ X vermelho = Fatura indisponível na COPEL
    - ✅ Check verde = Fatura baixada com sucesso
    - ⚠️ Laranja = Erro ao baixar
  - Frontend: Linha de botões "COPEL Auto" para iniciar download por mês
  - Frontend: Indicador de progresso em tempo real durante download
  - Alterações em:
    - `/app/backend/server.py`: Modelo InvoiceDownloadStatus, endpoints e background task
    - `/app/frontend/src/pages/PlantDetail.jsx`: Estados, funções e UI para download

- [x] **Integração Solarman (Parcial)** (09/03/2026): Estrutura inicial para integração com portal Solarman (Deye/Sofar):
  - Backend: Serviço `solarman_service.py` com Playwright
  - Backend: Endpoints `/api/integrations/solarman/login` e `/api/portals/solarman/import-plants`
  - Frontend: Card "Deye / Sofar (Solarman)" na página Portais
  - Frontend: Formulário com campos Email, Senha, Servidor, Grupo
  - **NOTA**: Web scraping está com dificuldades devido a CAPTCHA. Aguardando API oficial (APP_ID/SECRET solicitados).

## P1 - Upcoming
- [ ] Frontend para gerenciamento do Sistema de Créditos (distribuição entre UCs)
- [ ] Adicionar seção de detalhamento por UC beneficiária no relatório PDF (dados das faturas)
- [ ] Implementar integrações com outros portais (Huawei FusionSolar, Deye/Sofar Solarman, Solis)

## P2 - Backlog
- [ ] Integração com outras marcas de inversores
- [ ] Resolver automação COPEL (bloqueada por reCAPTCHA)
- [ ] Parser para faturas Energisa MS
- [ ] Remover obrigatoriedade do campo "Potência (kWp)" quando usina é sincronizada com Growatt
- [ ] Download de dados históricos da Growatt (funcionalidade ainda não implementada)

## Credentials
- Admin: projetos.onsolucoes@gmail.com / on123456
- Growatt: BTAVB001 / Comercial2023
