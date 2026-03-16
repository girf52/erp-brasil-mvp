from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from core.deps import get_db, get_current_user
from models.financeiro import NaturezaConta, TipoConta
from services import financeiro as svc

router = APIRouter(prefix="/api/financeiro", tags=["financeiro"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class PlanoContasIn(BaseModel):
    codigo: str
    descricao: str
    natureza: NaturezaConta
    tipo: TipoConta = TipoConta.ANALITICA
    conta_pai_id: Optional[int] = None


class PlanoContasOut(BaseModel):
    id: int
    codigo: str
    descricao: str
    natureza: NaturezaConta
    tipo: TipoConta
    conta_pai_id: Optional[int]
    ativo: bool

    model_config = {"from_attributes": True}


class LancamentoIn(BaseModel):
    data_competencia: date
    data_pagamento: Optional[date] = None
    historico: str
    debito_conta_id: int
    credito_conta_id: int
    valor_centavos: int
    centro_custo: Optional[str] = None

    @field_validator("valor_centavos")
    @classmethod
    def valor_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("valor_centavos deve ser maior que zero")
        return v


class LancamentoOut(BaseModel):
    id: int
    data_competencia: date
    data_pagamento: Optional[date]
    historico: str
    debito_conta_id: int
    credito_conta_id: int
    valor_centavos: int
    centro_custo: Optional[str]
    usuario_id: Optional[int]

    model_config = {"from_attributes": True}


# ─── Plano de Contas ──────────────────────────────────────────────────────────

@router.post("/plano-contas", response_model=PlanoContasOut, status_code=201)
def criar_conta(payload: PlanoContasIn, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.criar_conta(db, payload.codigo, payload.descricao, payload.natureza, payload.tipo, payload.conta_pai_id)


@router.get("/plano-contas", response_model=list[PlanoContasOut])
def listar_contas(apenas_ativas: bool = True, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.listar_contas(db, apenas_ativas)


# ─── Lançamentos ─────────────────────────────────────────────────────────────

@router.post("/lancamentos", response_model=LancamentoOut, status_code=201)
def criar_lancamento(payload: LancamentoIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return svc.criar_lancamento(
        db,
        data_competencia=payload.data_competencia,
        historico=payload.historico,
        debito_conta_id=payload.debito_conta_id,
        credito_conta_id=payload.credito_conta_id,
        valor_centavos=payload.valor_centavos,
        data_pagamento=payload.data_pagamento,
        centro_custo=payload.centro_custo,
        usuario_id=user.id,
    )


@router.get("/lancamentos", response_model=list[LancamentoOut])
def listar_lancamentos(
    inicio: Optional[date] = Query(None),
    fim: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return svc.listar_lancamentos(db, inicio, fim)


# ─── DRE ─────────────────────────────────────────────────────────────────────

@router.get("/dre")
def dre(
    inicio: date = Query(..., description="Data inicial (YYYY-MM-DD)"),
    fim: date = Query(..., description="Data final (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return svc.calcular_dre(db, inicio, fim)


# ─── Balancete ────────────────────────────────────────────────────────────────

@router.get("/balancete")
def balancete(
    data: date = Query(..., description="Data de referência (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return svc.calcular_balancete(db, data)
