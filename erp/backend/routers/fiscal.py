from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.deps import get_db, get_current_user
from models.fiscal import StatusNFe
from services import fiscal as svc

router = APIRouter(prefix="/api/fiscal", tags=["fiscal"])


class EmitirNFeIn(BaseModel):
    cnpj_emit: str
    cnpj_dest: str
    valor_total_centavos: int
    serie: int = 1


class CancelarNFeIn(BaseModel):
    motivo: str


class NFeOut(BaseModel):
    id: int; numero: int; serie: int
    chave_acesso: Optional[str]; cnpj_emit: str; cnpj_dest: str
    valor_total_centavos: int; status: str
    protocolo: Optional[str]; motivo_cancelamento: Optional[str]
    emitido_em: Optional[datetime]; cancelado_em: Optional[datetime]
    model_config = {"from_attributes": True}


@router.post("/nfe/emitir", response_model=NFeOut, status_code=201)
def emitir_nfe(payload: EmitirNFeIn, db: Session = Depends(get_db), _=Depends(get_current_user)):
    nf = svc.emitir_nfe(db, payload.cnpj_emit, payload.cnpj_dest,
                        payload.valor_total_centavos, payload.serie)
    return nf


@router.get("/nfe/{nfe_id}/xml")
def obter_xml(nfe_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    xml = svc.obter_xml(db, nfe_id)
    return Response(content=xml, media_type="application/xml")


@router.post("/nfe/{nfe_id}/cancelar", response_model=NFeOut)
def cancelar_nfe(nfe_id: int, payload: CancelarNFeIn,
                 db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.cancelar_nfe(db, nfe_id, payload.motivo)


@router.get("/nfe", response_model=list[NFeOut])
def listar_nfes(status: Optional[StatusNFe] = Query(None),
                db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.listar_nfes(db, status)
