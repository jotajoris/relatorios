# PRD - ON Soluções Energéticas - Sistema de Gestão de Usinas Solares

## Resumo do Projeto
Sistema web completo para gestão e geração de relatórios de usinas solares fotovoltaicas.

## Histórico de Implementação

### Fase 1 - MVP (Concluída em 18/02/2026)

**Backend (FastAPI + MongoDB)**
- ✅ Autenticação JWT com refresh tokens
- ✅ CRUD completo: Clientes, Usinas, Unidades Consumidoras
- ✅ Upload de dados de geração (Excel/CSV)
- ✅ Dashboard stats e reports endpoints
- ✅ Credenciais de inversores (estrutura)

**Frontend (React + TailwindCSS)**
- ✅ Login/Registro com design split-screen
- ✅ Dashboard com KPIs e gráficos
- ✅ Páginas: Clientes, Usinas, Detalhes da Usina
- ✅ Unidades Consumidoras
- ✅ Relatórios (preview)
- ✅ Configurações (estrutura para integrações)

**Infraestrutura**
- ✅ GitHub Actions CI/CD para Hostinger
- ✅ Documentação README.md
- ✅ Arquivos .env.example

## User Personas

1. **Administrador ON Soluções**
   - Gerencia múltiplas usinas de clientes
   - Precisa gerar relatórios mensais profissionais
   - Monitora desempenho de todas as usinas

2. **Técnico de Campo**
   - Verifica status das usinas
   - Faz upload de dados de geração
   - Cadastra novas UCs

## Requisitos Core (Implementados)

| Requisito | Status |
|-----------|--------|
| Autenticação JWT | ✅ |
| Dashboard com KPIs | ✅ |
| CRUD Clientes | ✅ |
| CRUD Usinas | ✅ |
| CRUD Unidades Consumidoras | ✅ |
| Upload Excel/CSV | ✅ |
| Gráficos de geração | ✅ |
| Preview de relatórios | ✅ |
| Design amarelo/preto | ✅ |
| Texto em pt-BR | ✅ |

## Backlog Prioritizado

### P0 - Crítico (Próxima sprint)
1. **Geração de PDF** - Usar Puppeteer para render HTML→PDF
2. **Integração Growatt API** - Sincronização automática de dados

### P1 - Alta Prioridade
3. **Automação COPEL** - Playwright para download de faturas
4. **Parsing de faturas PDF** - Extrair dados automaticamente
5. **Cron job para sincronização** - Rodar a cada 24h

### P2 - Média Prioridade
6. **Integração FusionSolar**
7. **Integração SolarMan**
8. **Integração Sungrow**
9. **Email automático de relatórios**
10. **Dashboard de alertas avançado**

### P3 - Baixa Prioridade
11. **App mobile (PWA)**
12. **Multi-tenancy**
13. **API pública para clientes**

## Próximos Passos Imediatos

1. Implementar geração de PDF com Puppeteer
2. Integrar API Growatt usando biblioteca growattServer
3. Implementar automação COPEL com Playwright
4. Adicionar cron jobs para sincronização automática
5. Testes end-to-end completos

## Tecnologias Utilizadas

- **Frontend**: React 19, TailwindCSS, Shadcn/UI, Recharts
- **Backend**: FastAPI, MongoDB, Motor
- **Auth**: JWT, bcrypt
- **Deploy**: GitHub Actions, Hostinger FTP
