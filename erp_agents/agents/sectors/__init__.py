# ERP Agents — Setores
from agents.sectors.financeiro      import get_financeiro_agents
from agents.sectors.fiscal          import get_fiscal_agents
from agents.sectors.rh_folha        import get_rh_agents
from agents.sectors.vendas_estoque  import get_vendas_estoque_agents
from agents.sectors.automacao_ia    import get_automacao_agents, get_robot_schedule

SECTOR_FACTORIES = {
    "financeiro":     get_financeiro_agents,
    "fiscal":         get_fiscal_agents,
    "rh_folha":       get_rh_agents,
    "vendas_estoque": get_vendas_estoque_agents,
    "automacao_ia":   get_automacao_agents,
}

def get_sector_agents(sector_id: str) -> dict:
    factory = SECTOR_FACTORIES.get(sector_id)
    if not factory:
        raise ValueError(f"Setor desconhecido: {sector_id}")
    return factory()
