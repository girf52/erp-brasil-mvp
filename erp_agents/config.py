"""
ERP Agents — Configuração Central (v2.0)
Arquitetura em 3 camadas: Maestro → Setores → Sub-agentes + Setor de Automação IA
"""
import os
from dataclasses import dataclass

# ─── Modelos ───────────────────────────────────────────────────────────────
MAESTRO_MODEL    = "claude-opus-4-6"
SPECIALIST_MODEL = "claude-sonnet-4-6"
WORKER_MODEL     = "claude-sonnet-4-6"

# ─── Configuração base de agente ──────────────────────────────────────────
@dataclass
class AgentConfig:
    name: str
    model: str
    max_tokens: int = 8192
    temperature: float = 0.2
    approval_required: bool = False
    sector: str = "global"
    role: str = "specialist"   # orchestrator | specialist | worker | reviewer | qa | robot

# ═══════════════════════════════════════════════════════════════════════════
#  CAMADA 1 — MAESTRO ERP
# ═══════════════════════════════════════════════════════════════════════════
MAESTRO_AGENT = AgentConfig(
    name="🎼 Maestro ERP", model=MAESTRO_MODEL,
    max_tokens=16000, temperature=0.3,
    approval_required=True, sector="global", role="orchestrator"
)

# ═══════════════════════════════════════════════════════════════════════════
#  CAMADA 2 — ORQUESTRADORES DE SETOR
# ═══════════════════════════════════════════════════════════════════════════
SECTOR_ORCHESTRATORS = {
    "financeiro":     AgentConfig("💰 Orquestrador Financeiro",   SPECIALIST_MODEL, 8192, 0.2, True,  "financeiro",      "orchestrator"),
    "fiscal":         AgentConfig("🧾 Orquestrador Fiscal",       MAESTRO_MODEL,    8192, 0.1, True,  "fiscal",          "orchestrator"),
    "rh_folha":       AgentConfig("👥 Orquestrador RH/Folha",     SPECIALIST_MODEL, 8192, 0.2, True,  "rh_folha",        "orchestrator"),
    "vendas_estoque": AgentConfig("🛒 Orquestrador Vendas/Est.",  SPECIALIST_MODEL, 8192, 0.2, False, "vendas_estoque",  "orchestrator"),
    "automacao_ia":   AgentConfig("🤖 Orquestrador Automação IA", MAESTRO_MODEL,    8192, 0.3, True,  "automacao_ia",    "orchestrator"),
    # Agentes globais (cross-setor)
    "arquiteto":      AgentConfig("🏛️ Arquiteto",                 SPECIALIST_MODEL, 8192, 0.1, False, "global",          "orchestrator"),
    "dev_frontend":   AgentConfig("🖥️  Dev Frontend",             WORKER_MODEL,     8192, 0.15,False, "global",          "worker"),
    "dba":            AgentConfig("🗄️ DBA",                       SPECIALIST_MODEL, 8192, 0.05,True,  "global",          "specialist"),
    "devops":         AgentConfig("🚀 DevOps",                    SPECIALIST_MODEL, 8192, 0.1, True,  "global",          "specialist"),
    "seguranca":      AgentConfig("🔒 Agente Segurança",          SPECIALIST_MODEL, 8192, 0.1, False, "global",          "specialist"),
}

# ═══════════════════════════════════════════════════════════════════════════
#  CAMADA 3A — SUB-AGENTES POR SETOR (Dev + QA + Revisor)
# ═══════════════════════════════════════════════════════════════════════════
SECTOR_SUBAGENTS = {
    # ── FINANCEIRO ───────────────────────────────────────────────────────
    "fin_dev":      AgentConfig("⚙️  Dev Financeiro",     WORKER_MODEL,     8192, 0.1,  False, "financeiro",     "worker"),
    "fin_qa":       AgentConfig("🧪 QA Financeiro",       SPECIALIST_MODEL, 8192, 0.15, False, "financeiro",     "qa"),
    "fin_revisor":  AgentConfig("🔎 Revisor Financeiro",  SPECIALIST_MODEL, 8192, 0.1,  True,  "financeiro",     "reviewer"),
    # ── FISCAL ───────────────────────────────────────────────────────────
    "fis_dev":      AgentConfig("⚙️  Dev Fiscal",         MAESTRO_MODEL,    8192, 0.05, True,  "fiscal",         "worker"),
    "fis_qa":       AgentConfig("🧪 QA Fiscal",           MAESTRO_MODEL,    8192, 0.05, True,  "fiscal",         "qa"),
    "fis_revisor":  AgentConfig("🔎 Revisor Fiscal",      MAESTRO_MODEL,    8192, 0.05, True,  "fiscal",         "reviewer"),
    # ── RH/FOLHA ─────────────────────────────────────────────────────────
    "rh_dev":       AgentConfig("⚙️  Dev RH/Folha",       WORKER_MODEL,     8192, 0.1,  False, "rh_folha",       "worker"),
    "rh_qa":        AgentConfig("🧪 QA RH/Folha",         SPECIALIST_MODEL, 8192, 0.1,  True,  "rh_folha",       "qa"),
    "rh_revisor":   AgentConfig("🔎 Revisor RH/Folha",    SPECIALIST_MODEL, 8192, 0.1,  True,  "rh_folha",       "reviewer"),
    # ── VENDAS/ESTOQUE ────────────────────────────────────────────────────
    "ve_dev":       AgentConfig("⚙️  Dev Vendas/Estoque", WORKER_MODEL,     8192, 0.1,  False, "vendas_estoque", "worker"),
    "ve_qa":        AgentConfig("🧪 QA Vendas/Estoque",   WORKER_MODEL,     8192, 0.2,  False, "vendas_estoque", "qa"),
    "ve_revisor":   AgentConfig("🔎 Revisor Vendas/Est.", WORKER_MODEL,     8192, 0.1,  False, "vendas_estoque", "reviewer"),
}

# ═══════════════════════════════════════════════════════════════════════════
#  CAMADA 3B — SETOR AUTOMAÇÃO IA (robôs de execução contínua)
# ═══════════════════════════════════════════════════════════════════════════
AUTOMATION_AGENTS = {
    "robot_sefaz":        AgentConfig("🤖 Robô SEFAZ",           SPECIALIST_MODEL, 8192, 0.05, False, "automacao_ia", "robot"),
    "robot_cadastro":     AgentConfig("🤖 Robô Cadastro",        SPECIALIST_MODEL, 8192, 0.1,  False, "automacao_ia", "robot"),
    "robot_audit_fiscal": AgentConfig("🤖 Auditor Fiscal IA",    MAESTRO_MODEL,    8192, 0.05, True,  "automacao_ia", "robot"),
    "robot_conciliacao":  AgentConfig("🤖 Robô Conciliação",     SPECIALIST_MODEL, 8192, 0.1,  True,  "automacao_ia", "robot"),
    "robot_cobranca":     AgentConfig("🤖 Agente de Cobrança",   SPECIALIST_MODEL, 8192, 0.2,  True,  "automacao_ia", "robot"),
    "robot_credito":      AgentConfig("🤖 Analista de Crédito",  SPECIALIST_MODEL, 8192, 0.2,  True,  "automacao_ia", "robot"),
}

# ─── Mapa global ──────────────────────────────────────────────────────────
ALL_AGENTS: dict[str, AgentConfig] = {
    "maestro_erp": MAESTRO_AGENT,
    **SECTOR_ORCHESTRATORS,
    **SECTOR_SUBAGENTS,
    **AUTOMATION_AGENTS,
}

# ─── Estrutura dos setores ────────────────────────────────────────────────
SECTOR_STRUCTURE = {
    "financeiro":     {"orchestrator": "financeiro",     "dev": "fin_dev", "qa": "fin_qa", "revisor": "fin_revisor"},
    "fiscal":         {"orchestrator": "fiscal",         "dev": "fis_dev", "qa": "fis_qa", "revisor": "fis_revisor"},
    "rh_folha":       {"orchestrator": "rh_folha",       "dev": "rh_dev",  "qa": "rh_qa",  "revisor": "rh_revisor"},
    "vendas_estoque": {"orchestrator": "vendas_estoque", "dev": "ve_dev",  "qa": "ve_qa",  "revisor": "ve_revisor"},
    "automacao_ia":   {"orchestrator": "automacao_ia",   "robots": list(AUTOMATION_AGENTS.keys())},
}

# ─── Módulos do ERP ───────────────────────────────────────────────────────
ERP_MODULES = [
    "financeiro",       # Plano de contas, lançamentos, contas a pagar/receber
    "vendas_crm",       # Clientes, pedidos, comissões
    "estoque",          # Produtos, movimentações, inventário
    "rh_folha",         # Funcionários, ponto, folha de pagamento
    "fiscal",           # NF-e, NFS-e, SPED, eSocial
]

TECH_STACK = {
    "backend":      "Python 3.12 + FastAPI + SQLAlchemy + Alembic",
    "frontend":     "React 18 + TypeScript + TailwindCSS + React Query",
    "database":     "PostgreSQL 16",
    "cache":        "Redis 7",
    "auth":         "Keycloak (RBAC + MFA)",
    "cloud":        "AWS (região sa-east-1 — São Paulo)",
    "ci_cd":        "GitHub Actions + Docker + ECR",
    "nfe_sdk":      "Nuvem Fiscal API",
    "open_banking": "Open Finance Brasil (Pluggy)",
    "task_queue":   "Celery + Redis",
    "scheduler":    "APScheduler (cron dos robôs)",
}

HUMAN_CHECKPOINTS = [
    "sprint_plan_approval", "destructive_migration", "fiscal_implementation",
    "security_critical", "pull_request_to_main", "production_deploy",
    "architecture_decision", "automation_production_enable",
    "credit_limit_change", "mass_collection_action",
    "fiscal_product_correction", "bank_reconciliation_divergence",
]

# ─── Alias de retrocompatibilidade ────────────────────────────────────────
AGENTS = ALL_AGENTS  # usado por maestro.py e specialized_agents.py (v1)

SAFETY_LIMITS = {
    "max_files_per_commit":              20,
    "max_tokens_per_task":               100_000,
    "max_automated_nfe_fetch":           500,
    "max_credit_limit_auto":             10_000,
    "max_collection_batch_auto":         50,
    "max_product_corrections_auto":      100,
    "reconciliation_divergence_alert":   1_000,
    "forbidden_commands": [
        "rm -rf /", "DROP DATABASE", "DELETE FROM",
        "git push --force origin main", "truncate",
    ],
    "protected_branches":    ["main", "production"],
    "required_test_coverage": 0.80,
}
