from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from core.deps import get_db, get_current_user
from models.vendas import Cliente, Produto, Pedido, StatusPedido
from models.fiscal import NotaFiscal, StatusNFe
from models.rh import Funcionario, Folha, StatusFuncionario
from models.financeiro import Lancamento

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/dashboard")
def dashboard_resumo(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """KPIs consolidados para o dashboard."""
    clientes = db.query(func.count(Cliente.id)).scalar() or 0
    produtos = db.query(func.count(Produto.id)).scalar() or 0
    pedidos_total = db.query(func.count(Pedido.id)).scalar() or 0
    pedidos_faturados = db.query(func.count(Pedido.id)).filter(
        Pedido.status == StatusPedido.FATURADO
    ).scalar() or 0
    faturamento = db.query(func.sum(Pedido.total_centavos)).filter(
        Pedido.status == StatusPedido.FATURADO
    ).scalar() or 0

    nfes_emitidas = db.query(func.count(NotaFiscal.id)).filter(
        NotaFiscal.status == StatusNFe.AUTORIZADA
    ).scalar() or 0
    nfes_canceladas = db.query(func.count(NotaFiscal.id)).filter(
        NotaFiscal.status == StatusNFe.CANCELADA
    ).scalar() or 0

    funcionarios_ativos = db.query(func.count(Funcionario.id)).filter(
        Funcionario.status == StatusFuncionario.ATIVO
    ).scalar() or 0
    folha_total = db.query(func.sum(Folha.salario_liquido)).scalar() or 0

    lancamentos = db.query(func.count(Lancamento.id)).scalar() or 0

    return {
        "clientes": clientes,
        "produtos": produtos,
        "pedidos_total": pedidos_total,
        "pedidos_faturados": pedidos_faturados,
        "faturamento_centavos": faturamento,
        "nfes_emitidas": nfes_emitidas,
        "nfes_canceladas": nfes_canceladas,
        "funcionarios_ativos": funcionarios_ativos,
        "folha_total_centavos": folha_total,
        "lancamentos": lancamentos,
    }
