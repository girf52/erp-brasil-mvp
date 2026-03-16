"""
ERP Agents — Fábrica Unificada de Agentes (v2.0)

Ponto único de criação de qualquer agente do sistema.
Suporta todos os 29 agentes: globais, setoriais e robôs de automação.

Uso:
    from agents.agent_factory import create_agent

    agent = create_agent("fin_dev")        # Sub-agente de setor
    agent = create_agent("robot_sefaz")    # Robô de automação
    agent = create_agent("arquiteto")      # Agente global
    agent = create_agent("financeiro")     # Orquestrador de setor
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from config import ALL_AGENTS, AgentConfig

if TYPE_CHECKING:
    from agents.base_agent import BaseAgent


# ─── Mapeamento de orquestradores de setor ─────────────────────────────────
# Os orquestradores estão em ALL_AGENTS com a chave = nome do setor (ex: "financeiro")
# mas cada módulo de setor os guarda internamente com sufixo "_orchestrator".
# Este mapa resolve a discrepância.
_ORCHESTRATOR_LOCAL_KEYS = {
    "financeiro":     "fin_orchestrator",
    "fiscal":         "fis_orchestrator",
    "rh_folha":       "rh_orchestrator",
    "vendas_estoque": "ve_orchestrator",
    "automacao_ia":   "auto_orchestrator",
}

# ─── Cache: evita recriar agentes a cada chamada ───────────────────────────
_agent_cache: dict[str, "BaseAgent"] = {}


def create_agent(agent_id: str, use_cache: bool = False) -> "BaseAgent":
    """
    Cria (ou recupera do cache) uma instância do agente pelo seu ID.

    Args:
        agent_id:  ID do agente conforme definido em ALL_AGENTS (config.py)
        use_cache: Se True, reutiliza instância já criada (útil para sprints longos)

    Returns:
        Instância configurada de BaseAgent pronta para .run()

    Raises:
        ValueError: Se o agent_id não existir em ALL_AGENTS
    """
    if agent_id not in ALL_AGENTS:
        available = ", ".join(sorted(ALL_AGENTS.keys()))
        raise ValueError(
            f"Agente desconhecido: '{agent_id}'.\n"
            f"IDs disponíveis: {available}"
        )

    if use_cache and agent_id in _agent_cache:
        return _agent_cache[agent_id]

    config: AgentConfig = ALL_AGENTS[agent_id]
    agent = _build_agent(agent_id, config)

    if use_cache:
        _agent_cache[agent_id] = agent

    return agent


def _build_agent(agent_id: str, config: AgentConfig) -> "BaseAgent":
    """Seleciona a factory correta com base no setor do agente."""
    from agents.base_agent import BaseAgent

    sector = config.sector

    # ── Agentes globais (arquiteto, dba, devops, seguranca, dev_backend, etc.) ──
    if sector == "global":
        return _create_global_agent(agent_id, config)

    # ── Setor Financeiro ────────────────────────────────────────────────────
    if sector == "financeiro":
        from agents.sectors.financeiro import get_financeiro_agents
        return _pick_from_sector(agent_id, get_financeiro_agents(), _ORCHESTRATOR_LOCAL_KEYS)

    # ── Setor Fiscal ────────────────────────────────────────────────────────
    if sector == "fiscal":
        from agents.sectors.fiscal import get_fiscal_agents
        return _pick_from_sector(agent_id, get_fiscal_agents(), _ORCHESTRATOR_LOCAL_KEYS)

    # ── Setor RH/Folha ──────────────────────────────────────────────────────
    if sector == "rh_folha":
        from agents.sectors.rh_folha import get_rh_agents
        return _pick_from_sector(agent_id, get_rh_agents(), _ORCHESTRATOR_LOCAL_KEYS)

    # ── Setor Vendas/Estoque ────────────────────────────────────────────────
    if sector == "vendas_estoque":
        from agents.sectors.vendas_estoque import get_vendas_estoque_agents
        return _pick_from_sector(agent_id, get_vendas_estoque_agents(), _ORCHESTRATOR_LOCAL_KEYS)

    # ── Setor Automação IA (robôs) ──────────────────────────────────────────
    if sector == "automacao_ia":
        from agents.sectors.automacao_ia import get_automacao_agents
        return _pick_from_sector(agent_id, get_automacao_agents(), _ORCHESTRATOR_LOCAL_KEYS)

    raise ValueError(f"Setor desconhecido para agente '{agent_id}': '{sector}'")


def _pick_from_sector(
    agent_id: str,
    sector_agents: dict,
    orchestrator_map: dict,
) -> "BaseAgent":
    """
    Procura o agente no dicionário retornado pela factory de setor.

    Trata a discrepância de nomes dos orquestradores: em ALL_AGENTS os
    orquestradores são chaveados pelo nome do setor (ex: "financeiro"),
    mas internamente as factories os chamam de "fin_orchestrator" etc.
    """
    # Tentativa direta (sub-agentes: fin_dev, fis_qa, robot_sefaz, ...)
    if agent_id in sector_agents:
        return sector_agents[agent_id]

    # Tentativa via mapeamento de orquestrador (financeiro → fin_orchestrator)
    local_key = orchestrator_map.get(agent_id)
    if local_key and local_key in sector_agents:
        return sector_agents[local_key]

    raise ValueError(
        f"Agente '{agent_id}' não encontrado na factory do setor. "
        f"Chaves disponíveis: {list(sector_agents.keys())}"
    )


def _create_global_agent(agent_id: str, config: AgentConfig) -> "BaseAgent":
    """
    Cria agentes globais usando os prompts de specialized_agents.py.
    Também adiciona ferramentas extras conforme o papel do agente.
    """
    from agents.base_agent import BaseAgent
    from agents.specialized_agents import SYSTEM_PROMPTS

    if agent_id not in SYSTEM_PROMPTS:
        raise ValueError(
            f"System prompt não definido para agente global '{agent_id}'. "
            f"Adicione-o em agents/specialized_agents.py → SYSTEM_PROMPTS."
        )

    agent = BaseAgent(agent_id, config, SYSTEM_PROMPTS[agent_id])

    # Ferramentas extras por papel
    _add_dev_tools(agent) if config.role == "worker" else None
    _add_dev_tools(agent) if agent_id in ("dev_backend", "dev_frontend", "especialista_fiscal", "dba") else None
    _add_qa_tools(agent) if agent_id == "qa" else None

    return agent


def _add_dev_tools(agent: "BaseAgent") -> None:
    """Adiciona ferramentas de desenvolvimento (git) ao agente."""
    git_tools = [
        {
            "name": "create_feature_branch",
            "description": "Cria uma branch de feature no GitHub",
            "input_schema": {
                "type": "object",
                "properties": {
                    "branch_name": {"type": "string"},
                    "from_branch": {"type": "string", "default": "main"},
                },
                "required": ["branch_name"],
            },
        },
        {
            "name": "commit_files",
            "description": "Faz commit de arquivos (Conventional Commits)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "files":   {"type": "array", "items": {"type": "string"}},
                    "message": {"type": "string"},
                },
                "required": ["files", "message"],
            },
        },
        {
            "name": "push_branch",
            "description": "Faz push da branch para o repositório remoto",
            "input_schema": {
                "type": "object",
                "properties": {"branch_name": {"type": "string"}},
                "required": ["branch_name"],
            },
        },
    ]
    # Evita duplicatas
    existing_names = {t["name"] for t in agent.tools}
    for tool in git_tools:
        if tool["name"] not in existing_names:
            agent.tools.append(tool)


def _add_qa_tools(agent: "BaseAgent") -> None:
    """Adiciona ferramentas de QA ao agente."""
    qa_tools = [
        {
            "name": "create_issue",
            "description": "Cria uma Issue de bug no GitHub",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title":  {"type": "string"},
                    "body":   {"type": "string"},
                    "labels": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "body"],
            },
        }
    ]
    existing_names = {t["name"] for t in agent.tools}
    for tool in qa_tools:
        if tool["name"] not in existing_names:
            agent.tools.append(tool)


def list_agents(sector: str | None = None) -> list[str]:
    """Retorna a lista de IDs de agentes disponíveis, opcionalmente filtrada por setor."""
    if sector:
        return [k for k, v in ALL_AGENTS.items() if v.sector == sector]
    return list(ALL_AGENTS.keys())
