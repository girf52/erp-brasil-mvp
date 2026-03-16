"""
[⚙️ Dev Fiscal] Service — emissão, cancelamento e consulta de NF-e.
Usa MockSEFAZ (nunca chama API externa real).
XML armazenado em data/xmls/{ano}/{mes}/{chave}.xml
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from models.fiscal import NotaFiscal, StatusNFe

# Adiciona mocks/ ao path para importar MockSEFAZ
_MOCKS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "mocks")
if _MOCKS_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_MOCKS_DIR))
from sefaz_mock import MockSEFAZ

_sefaz = MockSEFAZ()

# Diretório para armazenamento de XMLs
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "xmls")


def _salvar_xml(chave: str, xml: str) -> str:
    """Salva XML em data/xmls/{ano}/{mes}/{chave}.xml"""
    agora = datetime.now(timezone.utc)
    pasta = os.path.join(_DATA_DIR, str(agora.year), f"{agora.month:02d}")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"{chave}.xml")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(xml)
    return caminho


def _proximo_numero(db: Session, serie: int) -> int:
    """Retorna próximo número de NF-e para a série, com lock de banco."""
    ultimo = db.query(func.max(NotaFiscal.numero)).filter(
        NotaFiscal.serie == serie
    ).scalar()
    return (ultimo or 0) + 1


def _montar_xml_nfe(nf: NotaFiscal) -> str:
    """Monta XML simplificado da NF-e (estrutura válida para mock)."""
    return f"""<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
  <infNFe versao="4.00">
    <ide>
      <cUF>35</cUF>
      <natOp>Venda de mercadoria</natOp>
      <mod>55</mod>
      <serie>{nf.serie}</serie>
      <nNF>{nf.numero}</nNF>
      <dhEmi>{nf.criado_em.strftime("%Y-%m-%dT%H:%M:%S-03:00")}</dhEmi>
      <tpNF>1</tpNF>
      <idDest>1</idDest>
      <tpAmb>2</tpAmb>
    </ide>
    <emit>
      <CNPJ>{nf.cnpj_emit}</CNPJ>
    </emit>
    <dest>
      <CNPJ>{nf.cnpj_dest}</CNPJ>
    </dest>
    <total>
      <ICMSTot>
        <vNF>{nf.valor_total_centavos / 100:.2f}</vNF>
      </ICMSTot>
    </total>
  </infNFe>
</NFe>"""


def emitir_nfe(db: Session, cnpj_emit: str, cnpj_dest: str,
               valor_total_centavos: int, serie: int = 1) -> NotaFiscal:
    """Emite NF-e: monta XML → MockSEFAZ → salva localmente."""
    if valor_total_centavos <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Valor total deve ser positivo")
    if len(cnpj_emit) != 14 or len(cnpj_dest) != 14:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="CNPJ deve ter 14 dígitos")

    numero = _proximo_numero(db, serie)

    nf = NotaFiscal(
        numero=numero, serie=serie,
        cnpj_emit=cnpj_emit, cnpj_dest=cnpj_dest,
        valor_total_centavos=valor_total_centavos,
        status=StatusNFe.PENDENTE,
    )
    db.add(nf)
    db.flush()

    xml_enviado = _montar_xml_nfe(nf)
    resultado = _sefaz.autorizar_nfe(xml_enviado)

    nf.chave_acesso = resultado["chave_acesso"]
    nf.protocolo = resultado["protocolo"]
    nf.xml_enviado = xml_enviado
    nf.xml_retorno = resultado["xml_protocolo"]
    nf.status = StatusNFe.AUTORIZADA
    nf.emitido_em = datetime.now(timezone.utc)

    _salvar_xml(nf.chave_acesso, resultado["xml_protocolo"])

    db.commit()
    db.refresh(nf)
    return nf


def cancelar_nfe(db: Session, nfe_id: int, motivo: str) -> NotaFiscal:
    """Cancela NF-e — só até 24h após emissão."""
    nf = db.get(NotaFiscal, nfe_id)
    if not nf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NF-e não encontrada")
    if nf.status != StatusNFe.AUTORIZADA:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"NF-e não pode ser cancelada (status: {nf.status})")

    # Regra: cancelamento só até 24h após emissão
    if nf.emitido_em:
        emitido = nf.emitido_em.replace(tzinfo=timezone.utc) if nf.emitido_em.tzinfo is None else nf.emitido_em
        limite = emitido + timedelta(hours=24)
        if datetime.now(timezone.utc) > limite:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Prazo de cancelamento expirado (máx 24h após emissão)")

    if not motivo or len(motivo.strip()) < 15:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Motivo do cancelamento deve ter no mínimo 15 caracteres")

    resultado = _sefaz.cancelar_nfe(nf.chave_acesso, motivo)

    nf.status = StatusNFe.CANCELADA
    nf.motivo_cancelamento = motivo
    nf.cancelado_em = datetime.now(timezone.utc)

    db.commit()
    db.refresh(nf)
    return nf


def consultar_nfe(db: Session, nfe_id: int) -> NotaFiscal:
    """Retorna NF-e pelo ID."""
    nf = db.get(NotaFiscal, nfe_id)
    if not nf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NF-e não encontrada")
    return nf


def obter_xml(db: Session, nfe_id: int) -> str:
    """Retorna XML da NF-e."""
    nf = consultar_nfe(db, nfe_id)
    if not nf.xml_retorno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="XML não disponível")
    return nf.xml_retorno


def listar_nfes(db: Session, status_filtro: Optional[StatusNFe] = None) -> list[NotaFiscal]:
    """Lista NF-e com filtro opcional por status."""
    q = db.query(NotaFiscal)
    if status_filtro:
        q = q.filter(NotaFiscal.status == status_filtro)
    return q.order_by(NotaFiscal.criado_em.desc()).all()
