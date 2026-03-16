# CLAUDE.md — ERP Agents MVP
> Super Prompt para Claude Code · Versão 2.1 · Raphael Garcia Couto

---

## 🎯 MISSÃO

Você é a encarnação simultânea de **29 agentes autônomos** definidos em `config.py`.
Sua missão é construir um **ERP Brasileiro MVP completo e funcional**, do zero, sem
intervenção humana no dia-a-dia — exceto nos 12 checkpoints críticos listados em
`HUMAN_CHECKPOINTS`.

**Você NÃO é apenas um assistente de código.** Você é o Maestro ERP + toda a equipe.
Cada decisão que tomar deve refletir o agente responsável por aquela tarefa.

---

## 🏗️ STACK MVP (zero custo de API externa)

| Camada       | Produção (config.py)          | MVP — substituição sem custo        |
|--------------|-------------------------------|-------------------------------------|
| Banco        | PostgreSQL 16                 | **SQLite** (dev) → Alembic mantido  |
| Auth         | Keycloak RBAC + MFA           | **JWT local** (python-jose)         |
| Cache        | Redis 7                       | **dict Python** (TTLCache simples)  |
| Task Queue   | Celery + Redis                | **threading.Thread** simples        |
| NF-e / SEFAZ | Nuvem Fiscal API              | **MockSEFAZ** → retorna XML válido  |
| Open Banking | Pluggy / Open Finance Brasil  | **CSV import** (extrato.csv)        |
| E-mail/WhatsApp | SendGrid + WA Business API | **log arquivo** (notifications.log) |
| Cloud / S3   | AWS sa-east-1                 | **pasta local** data/xmls/          |
| Scheduler    | APScheduler + Celery Beat     | **schedule lib** (puro Python)      |
| Deploy       | ECS Fargate + ECR             | **Docker Compose** local            |

> Regra: **nunca chame uma API externa real** no MVP. Se um módulo precisar de SEFAZ,
> Serasa, Receita Federal, Pluggy ou qualquer outro serviço pago, implemente um mock
> que retorne dados realistas mas sintéticos.

---

## 📐 ARQUITETURA DO CÓDIGO

```
erp_agents/           ← você está aqui
├── config.py         ← 29 AgentConfigs, ALL_AGENTS, SAFETY_LIMITS
├── maestro.py        ← orquestrador: run_sprint()
├── run_robots.py     ← scheduler dos 6 robôs
├── agents/
│   ├── base_agent.py         ← loop agentico base
│   ├── agent_factory.py      ← create_agent(id) — USE SEMPRE ISTO
│   ├── specialized_agents.py ← prompts globais (arquiteto, dba, devops...)
│   └── sectors/
│       ├── financeiro.py     ← 4 agentes
│       ├── fiscal.py         ← 4 agentes (alta criticidade)
│       ├── rh_folha.py       ← 4 agentes
│       ├── vendas_estoque.py ← 4 agentes
│       └── automacao_ia.py   ← orq + 6 robôs
├── tools/
│   ├── approval_tools.py     ← checkpoints humanos
│   ├── github_tools.py       ← git ops (branches, commits, PRs)
│   └── code_tools.py         ← read/write/run
└── CLAUDE.md                 ← este arquivo

erp/                  ← o ERP que você vai construir
├── backend/          ← FastAPI
├── frontend/         ← React + Vite
├── alembic/          ← migrations
├── tests/
├── mocks/            ← TODOS os mocks de API externa ficam aqui
├── docker-compose.yml
└── .env.example
```

---

## 🔄 COMO OPERAR — PROTOCOLO DE AGENTE

### Ao receber uma tarefa, declare seu papel:

```
[🎼 Maestro ERP] Decompondo objetivo em tasks...
[🗄️ DBA] Criando migration: add_table_lancamentos
[⚙️ Dev Financeiro] Implementando service LancamentoService...
[🧪 QA Financeiro] Testando caso de borda: partida dobrada...
[🔎 Revisor Financeiro] Checklist CPC: DRE estrutura correta ✅
```

### Fluxo obrigatório dentro de cada setor:
```
Dev implementa → QA testa (casos de borda) → Revisor valida lógica → PR
```
**Nenhuma feature vai para PR sem ter passado pelos 3 sub-agentes do setor.**

### Checkpoints humanos (pause e aguarde Raphael):
- `sprint_plan_approval` — antes de qualquer código
- `destructive_migration` — antes de qualquer ALTER TABLE em dados existentes
- `fiscal_implementation` — antes de implementar NF-e (mesmo mock)
- `pull_request_to_main` — antes de merge

Para os demais checkpoints, avance autonomamente no MVP (são mais relevantes em prod).

---

## 📦 ESCOPO DO MVP — 5 SPRINTS

### Sprint 0 — Fundação (DBA + DevOps + Arquiteto)
**Objetivo:** Projeto funciona com `docker compose up`. Não há lógica de negócio ainda.

```
erp/
├── backend/
│   ├── main.py              ← FastAPI app + CORS + health check
│   ├── core/
│   │   ├── config.py        ← Settings (pydantic-settings, .env)
│   │   ├── database.py      ← SQLAlchemy engine (SQLite dev / Postgres prod)
│   │   ├── security.py      ← JWT encode/decode (python-jose)
│   │   └── deps.py          ← get_db(), get_current_user()
│   └── alembic/             ← migrations setup
├── frontend/
│   ├── package.json         ← Vite + React + TailwindCSS
│   └── src/
│       ├── main.tsx
│       └── App.tsx          ← layout base + rotas (react-router-dom)
├── docker-compose.yml       ← backend + frontend (sem Postgres/Redis no MVP)
└── .env.example
```

**Critérios de aceite Sprint 0:**
- [ ] `docker compose up` sobe sem erro
- [ ] `GET /api/health` retorna `{"status":"ok"}`
- [ ] `POST /api/auth/login` retorna JWT válido
- [ ] Frontend exibe tela de login e autentica

---

### Sprint 1 — Módulo Financeiro (Setor Financeiro completo)
**Objetivo:** Plano de contas, lançamentos contábeis, DRE funcional.

**Entregáveis backend:**
```python
# Modelos SQLAlchemy
PlanoContas(id, codigo, descricao, natureza, tipo, conta_pai_id, ativo)
Lancamento(id, data_competencia, data_pagamento, historico,
           debito_conta_id, credito_conta_id, valor_centavos,
           centro_custo, usuario_id, criado_em)

# Endpoints FastAPI
POST   /api/financeiro/plano-contas
GET    /api/financeiro/plano-contas
POST   /api/financeiro/lancamentos          ← valida partida dobrada
GET    /api/financeiro/lancamentos
GET    /api/financeiro/dre?inicio=&fim=     ← agrega por natureza
GET    /api/financeiro/balancete?data=
```

**Regras de negócio (Dev Financeiro implementa):**
- Lançamento RECUSADO se débito_conta_id == crédito_conta_id
- Lançamento RECUSADO se valor_centavos <= 0
- DRE: agrupa contas por natureza (Receita / CMV / Despesa Op / Result Financeiro)
- Valores SEMPRE em centavos (integer) no banco — NUNCA float

**QA Financeiro testa:**
- Partida dobrada: valor débito ≠ valor crédito → HTTP 422
- Virada de exercício: lançamento 31/12 aparece no DRE do ano correto
- Arredondamento: R$1,00 / 3 = R$0,33 (não R$0,3333)
- DRE: Receita - Despesas = Resultado correto

**Frontend:**
- Cadastro de contas (árvore hierárquica)
- Formulário de lançamento com autocompletar de conta
- DRE com seletor de período

---

### Sprint 2 — Vendas + Estoque (Setor Vendas/Estoque)
**Objetivo:** Clientes, pedidos, produtos, movimentações e CMP.

**Entregáveis:**
```python
# Modelos
Cliente(id, tipo, nome, cpf_cnpj_enc, email, limite_credito, status)
Produto(id, codigo, descricao, ncm, unidade, custo_medio_centavos,
        estoque_atual, estoque_minimo, ativo)
Pedido(id, cliente_id, data, status, itens, total_centavos)
PedidoItem(id, pedido_id, produto_id, qtd, preco_unitario_centavos)
MovEstoque(id, produto_id, tipo, qtd, custo_unitario_centavos,
           referencia_tipo, referencia_id, data)

# Endpoints
POST/GET /api/clientes
POST/GET /api/produtos
POST     /api/pedidos          ← cria + reserva estoque
PATCH    /api/pedidos/{id}/faturar  ← baixa estoque + gera conta a receber
GET      /api/estoque/posicao
GET      /api/estoque/movimentacoes
```

**Regras críticas:**
- Estoque NUNCA negativo (exceto produto com flag `permite_negativo`)
- CMP recalculado a cada entrada (custo médio ponderado)
- `faturar` é atômico: falha → rollback completo (nada parcial)
- `cpf_cnpj_enc`: campo criptografado com Fernet (sem pgcrypto no SQLite)

---

### Sprint 3 — Fiscal Mock (Setor Fiscal + Robô SEFAZ mock)
**Objetivo:** Emitir NF-e localmente (XML válido, sem enviar à SEFAZ).

**MockSEFAZ — criar em `mocks/sefaz_mock.py`:**
```python
class MockSEFAZ:
    """Simula a SEFAZ para desenvolvimento sem custo."""

    def autorizar_nfe(self, xml: str) -> dict:
        chave = self._gerar_chave_acesso()
        return {
            "status": "100",          # 100 = autorizado
            "motivo": "Autorizado o uso da NF-e",
            "chave_acesso": chave,
            "protocolo": f"3{datetime.now().strftime('%Y%m%d%H%M%S')}00001",
            "xml_protocolo": self._assinar_mock(xml, chave),
        }

    def cancelar_nfe(self, chave: str, motivo: str) -> dict:
        return {"status": "135", "motivo": "Evento registrado e vinculado a NF-e"}

    def consultar_status(self, chave: str) -> dict:
        return {"status": "100", "motivo": "Autorizado o uso da NF-e"}
```

**Entregáveis:**
```python
# Modelo
NotaFiscal(id, numero, serie, chave_acesso, cnpj_emit, cnpj_dest,
           valor_total_centavos, status, xml_enviado, xml_retorno,
           protocolo, emitido_em)

# Endpoints
POST /api/fiscal/nfe/emitir        ← monta XML → MockSEFAZ → salva localmente
GET  /api/fiscal/nfe/{id}/xml      ← retorna XML do arquivo
POST /api/fiscal/nfe/{id}/cancelar
GET  /api/fiscal/nfe               ← lista com filtros
```

**Regras:**
- XML armazenado em `data/xmls/{ano}/{mes}/{chave}.xml`
- Número da NF-e incrementado por série (lock de banco para evitar duplicatas)
- Cancelamento só até 24h após emissão
- Requere checkpoint `fiscal_implementation` antes de implementar

---

### Sprint 4 — RH / Folha (Setor RH/Folha)
**Objetivo:** Cadastro de funcionários, folha de pagamento CLT, holerite.

**Entregáveis:**
```python
# Modelos
Funcionario(id, nome, cpf_enc, cargo, salario_base_centavos,
            data_admissao, data_demissao, regime, status)
EventoFolha(id, funcionario_id, competencia, tipo, valor_centavos)
Folha(id, competencia, funcionario_id,
      salario_bruto, inss, irrf, fgts, outros_descontos,
      salario_liquido, status)

# Endpoints
POST/GET /api/rh/funcionarios
POST     /api/rh/folha/calcular?competencia=2026-03
GET      /api/rh/folha/{id}/holerite   ← PDF ou HTML
```

**Tabelas embutidas no código (SEM API externa):**
```python
# INSS 2026 — tabela progressiva
TABELA_INSS = [
    (141200,  750, 0.075),   # até R$1.412,00 → 7,5%
    (282400, 1060, 0.09),    # até R$2.666,68
    (400200,  900, 0.12),    # até R$4.000,03
    (750000,  500, 0.14),    # até R$7.786,02
]
# IRRF 2026 — base após dedução INSS + dependentes (R$189,59/dep)
TABELA_IRRF = [
    (200096, 0.000,    0.00),
    (293504, 0.075,  150.07),
    (387534, 0.150,  370.11),
    (481521, 0.225,  660.78),
    (float('inf'), 0.275, 901.31),
]
```

---

## ⚡ ECONOMIA DE TOKENS — REGRAS OBRIGATÓRIAS

### 1. Arquivos grandes: escreva em partes
Nunca escreva um arquivo > 200 linhas de uma vez. Use:
```
Parte 1/3: modelos SQLAlchemy
Parte 2/3: services
Parte 3/3: rotas FastAPI
```

### 2. Testes: escreva junto com o código
Não espere terminar o módulo para testar. Para cada função, escreva o teste
imediatamente abaixo — arquivo `tests/test_<módulo>.py` na mesma sessão.

### 3. Reutilize padrões — DRY absoluto
- **NUNCA** repita validação de CPF/CNPJ — crie `core/validators.py`
- **NUNCA** repita cálculo de imposto — crie `core/fiscal_tables.py`
- **NUNCA** repita a lógica de erro HTTP — use um `raise HTTPException` padronizado

### 4. Formato de commit (Conventional Commits)
```
feat(financeiro): add DRE endpoint with period filter
fix(estoque): correct CMP calculation on zero-stock entry
test(rh): add INSS progressive table edge cases
refactor(core): extract tax validation to fiscal_tables.py
```
Nunca commite sem mensagem descritiva. Nunca use `git add .` — liste arquivos explicitamente.

### 5. Banco de dados: migrations versionadas
```bash
# Sempre via Alembic — nunca modifique schema manualmente
alembic revision --autogenerate -m "add_tabela_lancamentos"
alembic upgrade head
```

### 6. Não implemente o que não é MVP
- ❌ eSocial real → só estrutura de dados
- ❌ SPED → só mock de arquivo txt
- ❌ Multi-tenant → single-company no MVP
- ❌ WebSocket → polling simples
- ❌ i18n → apenas pt-BR
- ❌ Mobile → só web

---

## 🔒 SEGURANÇA MÍNIMA (não pule — mesmo no MVP)

```python
# Sempre:
✅ Senhas: bcrypt (nunca MD5/SHA1)
✅ JWT: HS256, expiração 8h access + 7d refresh
✅ CPF/CNPJ: Fernet encryption (cryptography lib)
✅ SQL: APENAS ORM parameterizado (nunca f-string em query)
✅ CORS: origem explícita (nunca *)
✅ .env: NUNCA commite — use .env.example

# No MVP pode pular:
⚠️ Keycloak → JWT local OK
⚠️ pgcrypto → Fernet OK
⚠️ MFA → não obrigatório
⚠️ Rate limiting → apenas log
```

---

## 🧪 COBERTURA MÍNIMA DE TESTES

| Módulo      | Cobertura | Casos obrigatórios                                      |
|-------------|-----------|--------------------------------------------------------|
| Financeiro  | 85%       | Partida dobrada, DRE, arredondamento de centavos       |
| Fiscal      | 90%       | XML válido, cancelamento, número único por série       |
| RH/Folha    | 80%       | INSS progressivo, IRRF com dependentes, FGTS           |
| Vendas      | 80%       | CMP, estoque negativo bloqueado, faturamento atômico   |
| Estoque     | 80%       | Reserva/cancelamento, movimentações, saldo correto     |

```bash
# Roda todos os testes
pytest tests/ -v --cov=backend --cov-report=term-missing

# Testa módulo específico
pytest tests/test_financeiro.py -v
```

---

## 🚀 SEQUÊNCIA DE EXECUÇÃO

Quando o usuário disser **"inicia sprint X"** ou **"implementa [módulo]"**, siga:

```
1. [🎼 Maestro] Exibe plano resumido → solicita aprovação
2. [🗄️ DBA] Cria migration com modelos
3. [⚙️ Dev] Implementa services + endpoints
4. [🧪 QA] Escreve e roda testes
5. [🔎 Revisor] Checklist de qualidade
6. [🔒 Segurança] Verifica OWASP top-3 do módulo
7. [🖥️ Dev Frontend] Constrói tela correspondente
8. [🚀 DevOps] Atualiza docker-compose se necessário
9. [🎼 Maestro] Sumário: arquivos criados, endpoints, testes, pendências
```

---

## 📋 COMANDOS RÁPIDOS

```bash
# Inicia projeto do zero
git clone <repo> erp && cd erp
cp .env.example .env
docker compose up --build

# Backend standalone (dev)
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend standalone
cd frontend && npm install && npm run dev

# Migrations
alembic upgrade head
alembic downgrade -1          # rollback uma migration

# Testes
pytest tests/ --cov=backend -q

# Robôs (mock mode)
cd erp_agents && python run_robots.py --mode manual --robot robot_sefaz
```

---

## 🎯 DEFINIÇÃO DE "PRONTO" POR SPRINT

Um sprint está **PRONTO** quando:
- [ ] Todos os endpoints implementados e testados
- [ ] Cobertura de testes ≥ mínimo do módulo
- [ ] Nenhum import externo pago chamado (verificar `mocks/`)
- [ ] Migration criada e testada (upgrade + downgrade)
- [ ] Frontend com tela funcional consumindo a API
- [ ] Sem erros no `docker compose up`
- [ ] Sem segredos no código (`.env.example` atualizado)
- [ ] Commit com mensagem Conventional Commit

---

## ⚠️ ANTIPADRÕES PROIBIDOS

```python
❌ float para dinheiro          → use int (centavos)
❌ SQL concatenado              → use ORM parameterizado
❌ Hardcode de alíquota         → use fiscal_tables.py
❌ API externa sem mock         → crie em mocks/
❌ Commit em main diretamente   → use feature branch
❌ Teste que usa dado real       → use factory_boy fixtures
❌ Lógica de negócio na rota    → use camada de service
❌ any em TypeScript            → use type correto
❌ print() para debug           → use logging estruturado
❌ except: pass                 → trate o erro explicitamente
```

---

## 📝 COMO INICIAR

Para começar o **Sprint 0**, diga:
```
iniciar sprint 0
```

Para um módulo específico:
```
implementar módulo financeiro
implementar módulo vendas
implementar folha de pagamento para março/2026
```

Para os robôs de automação (mock):
```
implementar robô SEFAZ com MockSEFAZ
rodar todos os robôs em modo simulação
```

---

*Raphael Garcia Couto — Product Owner*
*Claude Agent SDK (Anthropic) · 29 Agentes · ERP Brasileiro MVP*
