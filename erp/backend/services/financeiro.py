"""
[⚙️ Dev Financeiro] Service — regras de negócio do módulo financeiro.
Regras: partida dobrada, valores em centavos, DRE por natureza.
"""
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from models.financeiro import PlanoContas, Lancamento, NaturezaConta, TipoConta


# ─── Plano de Contas ──────────────────────────────────────────────────────────

def criar_conta(db: Session, codigo: str, descricao: str, natureza: NaturezaConta,
                tipo: TipoConta = TipoConta.ANALITICA, conta_pai_id: Optional[int] = None) -> PlanoContas:
    if db.query(PlanoContas).filter(PlanoContas.codigo == codigo).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Código {codigo} já existe no plano de contas")
    if conta_pai_id:
        pai = db.get(PlanoContas, conta_pai_id)
        if not pai:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta pai não encontrada")
        if pai.tipo == TipoConta.ANALITICA:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Conta pai não pode ser analítica")
    conta = PlanoContas(codigo=codigo, descricao=descricao, natureza=natureza, tipo=tipo, conta_pai_id=conta_pai_id)
    db.add(conta)
    db.commit()
    db.refresh(conta)
    return conta


def listar_contas(db: Session, apenas_ativas: bool = True) -> list[PlanoContas]:
    q = db.query(PlanoContas)
    if apenas_ativas:
        q = q.filter(PlanoContas.ativo == True)  # noqa: E712
    return q.order_by(PlanoContas.codigo).all()


# ─── Lançamentos ─────────────────────────────────────────────────────────────

def criar_lancamento(db: Session, data_competencia: date, historico: str,
                     debito_conta_id: int, credito_conta_id: int,
                     valor_centavos: int, data_pagamento: Optional[date] = None,
                     centro_custo: Optional[str] = None, usuario_id: Optional[int] = None) -> Lancamento:
    # Regra: valor deve ser positivo
    if valor_centavos <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="valor_centavos deve ser maior que zero")

    # Regra: débito ≠ crédito (partida dobrada)
    if debito_conta_id == credito_conta_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="Conta de débito e crédito não podem ser iguais (partida dobrada)")

    # Validar contas existem e são analíticas
    for conta_id, lado in [(debito_conta_id, "débito"), (credito_conta_id, "crédito")]:
        conta = db.get(PlanoContas, conta_id)
        if not conta:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Conta de {lado} não encontrada")
        if conta.tipo != TipoConta.ANALITICA:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                                detail=f"Conta de {lado} deve ser analítica (não sintética)")
        if not conta.ativo:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                                detail=f"Conta de {lado} está inativa")

    lancamento = Lancamento(
        data_competencia=data_competencia,
        data_pagamento=data_pagamento,
        historico=historico,
        debito_conta_id=debito_conta_id,
        credito_conta_id=credito_conta_id,
        valor_centavos=valor_centavos,
        centro_custo=centro_custo,
        usuario_id=usuario_id,
    )
    db.add(lancamento)
    db.commit()
    db.refresh(lancamento)
    return lancamento


def listar_lancamentos(db: Session, inicio: Optional[date] = None, fim: Optional[date] = None) -> list[Lancamento]:
    q = db.query(Lancamento)
    if inicio:
        q = q.filter(Lancamento.data_competencia >= inicio)
    if fim:
        q = q.filter(Lancamento.data_competencia <= fim)
    return q.order_by(Lancamento.data_competencia.desc(), Lancamento.id.desc()).all()


# ─── DRE ─────────────────────────────────────────────────────────────────────

_GRUPOS_DRE = [
    ("Receita Bruta", [NaturezaConta.RECEITA]),
    ("CMV / CPV", [NaturezaConta.CMV]),
    ("Despesas Operacionais", [NaturezaConta.DESPESA]),
    ("Resultado Financeiro", [NaturezaConta.RESULTADO_FINANCEIRO]),
]

_NATUREZAS_RECEITA = {NaturezaConta.RECEITA}
_NATUREZAS_CUSTO   = {NaturezaConta.CMV, NaturezaConta.DESPESA, NaturezaConta.RESULTADO_FINANCEIRO}


def _soma_natureza(db: Session, naturezas: list[NaturezaConta], inicio: date, fim: date) -> int:
    """Soma valor_centavos dos lançamentos cujas contas (crédito para receita, débito para custo) têm a natureza dada."""
    total = 0
    contas_ids = [c.id for c in db.query(PlanoContas.id).filter(PlanoContas.natureza.in_(naturezas)).all()]
    if not contas_ids:
        return 0
    for conta_id in contas_ids:
        nat = db.query(PlanoContas.natureza).filter(PlanoContas.id == conta_id).scalar()
        if nat in _NATUREZAS_RECEITA:
            # Receita: valor lançado a crédito nessa conta
            v = db.query(func.sum(Lancamento.valor_centavos)).filter(
                Lancamento.credito_conta_id == conta_id,
                Lancamento.data_competencia >= inicio,
                Lancamento.data_competencia <= fim,
            ).scalar() or 0
        else:
            # Custo/Despesa: valor lançado a débito nessa conta
            v = db.query(func.sum(Lancamento.valor_centavos)).filter(
                Lancamento.debito_conta_id == conta_id,
                Lancamento.data_competencia >= inicio,
                Lancamento.data_competencia <= fim,
            ).scalar() or 0
        total += v
    return total


def calcular_dre(db: Session, inicio: date, fim: date) -> dict:
    linhas = []
    receita_bruta = 0
    total_custos = 0

    for grupo, naturezas in _GRUPOS_DRE:
        valor = _soma_natureza(db, naturezas, inicio, fim)
        linhas.append({"grupo": grupo, "valor_centavos": valor})
        if naturezas[0] in _NATUREZAS_RECEITA:
            receita_bruta += valor
        else:
            total_custos += valor

    resultado_liquido = receita_bruta - total_custos
    return {
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "linhas": linhas,
        "receita_bruta_centavos": receita_bruta,
        "total_custos_centavos": total_custos,
        "resultado_liquido_centavos": resultado_liquido,
    }


# ─── Balancete ────────────────────────────────────────────────────────────────

def calcular_balancete(db: Session, data_ref: date) -> list[dict]:
    contas = db.query(PlanoContas).filter(PlanoContas.tipo == TipoConta.ANALITICA, PlanoContas.ativo == True).order_by(PlanoContas.codigo).all()  # noqa: E712
    resultado = []
    for conta in contas:
        debitos = db.query(func.sum(Lancamento.valor_centavos)).filter(
            Lancamento.debito_conta_id == conta.id,
            Lancamento.data_competencia <= data_ref,
        ).scalar() or 0
        creditos = db.query(func.sum(Lancamento.valor_centavos)).filter(
            Lancamento.credito_conta_id == conta.id,
            Lancamento.data_competencia <= data_ref,
        ).scalar() or 0
        resultado.append({
            "conta_id": conta.id,
            "codigo": conta.codigo,
            "descricao": conta.descricao,
            "natureza": conta.natureza,
            "debitos_centavos": debitos,
            "creditos_centavos": creditos,
            "saldo_centavos": debitos - creditos,
        })
    return resultado
