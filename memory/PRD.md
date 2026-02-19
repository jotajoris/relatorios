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

## P1 - Upcoming
- [ ] Frontend para gerenciamento do Sistema de Créditos (distribuição entre UCs)
- [ ] Página de Gerenciamento de Clientes (CRUD + upload de logo)
- [ ] Adicionar seção de detalhamento por UC beneficiária no relatório PDF (dados das faturas)

## P2 - Backlog
- [ ] Job agendado para sincronização automática de dados da Growatt
- [ ] Integração com outras marcas de inversores
- [ ] Resolver automação COPEL (bloqueada por reCAPTCHA)
- [ ] Parser para faturas Energisa MS

## Credentials
- Admin: projetos.onsolucoes@gmail.com / on123456
- Growatt: BTAVB001 / Comercial2023
