from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.deps import get_db, get_current_user
from services import rh as svc

router = APIRouter(prefix="/api/rh", tags=["rh"])


# ── Schemas ──

class FuncionarioIn(BaseModel):
    nome: str
    cpf: str
    cargo: str
    salario_base_centavos: int
    data_admissao: date
    regime: str = "clt"
    dependentes: int = 0


class FuncionarioOut(BaseModel):
    id: int; nome: str; cpf: str; cargo: str
    salario_base_centavos: int; data_admissao: date
    data_demissao: Optional[date]; regime: str; status: str
    dependentes: int
    model_config = {"from_attributes": True}


class DemitirIn(BaseModel):
    data_demissao: date


class EventoIn(BaseModel):
    funcionario_id: int
    competencia: str
    tipo: str
    valor_centavos: int
    descricao: Optional[str] = None


class EventoOut(BaseModel):
    id: int; funcionario_id: int; competencia: str
    tipo: str; valor_centavos: int; descricao: Optional[str]
    model_config = {"from_attributes": True}


class FolhaOut(BaseModel):
    id: int; competencia: str; funcionario_id: int
    salario_bruto: int; inss: int; irrf: int; fgts: int
    outros_descontos: int; salario_liquido: int; status: str
    model_config = {"from_attributes": True}


# ── Endpoints ──

@router.post("/funcionarios", response_model=FuncionarioOut, status_code=201)
def criar_funcionario(payload: FuncionarioIn, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.criar_funcionario(
        db, payload.nome, payload.cpf, payload.cargo,
        payload.salario_base_centavos, payload.data_admissao,
        payload.regime, payload.dependentes,
    )


@router.get("/funcionarios", response_model=list[FuncionarioOut])
def listar_funcionarios(apenas_ativos: bool = Query(True),
                        db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.listar_funcionarios(db, apenas_ativos)


@router.post("/funcionarios/{func_id}/demitir", response_model=FuncionarioOut)
def demitir(func_id: int, payload: DemitirIn,
            db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.demitir_funcionario(db, func_id, payload.data_demissao)


@router.post("/eventos", response_model=EventoOut, status_code=201)
def criar_evento(payload: EventoIn, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.criar_evento(db, payload.funcionario_id, payload.competencia,
                            payload.tipo, payload.valor_centavos, payload.descricao)


@router.get("/eventos", response_model=list[EventoOut])
def listar_eventos(competencia: str = Query(...),
                   funcionario_id: Optional[int] = Query(None),
                   db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.listar_eventos(db, competencia, funcionario_id)


@router.post("/folha/calcular", response_model=list[FolhaOut])
def calcular_folha(competencia: str = Query(...),
                   db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.calcular_folha(db, competencia)


@router.get("/folha", response_model=list[FolhaOut])
def listar_folhas(competencia: Optional[str] = Query(None),
                  db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.listar_folhas(db, competencia)


@router.get("/folha/{folha_id}/holerite")
def holerite(folha_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.obter_holerite(db, folha_id)
