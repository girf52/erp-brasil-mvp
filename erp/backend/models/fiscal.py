from sqlalchemy import String, Integer, DateTime, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional
import enum
from core.database import Base


class StatusNFe(str, enum.Enum):
    PENDENTE = "pendente"
    AUTORIZADA = "autorizada"
    CANCELADA = "cancelada"
    REJEITADA = "rejeitada"


class NotaFiscal(Base):
    __tablename__ = "notas_fiscais"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(Integer, index=True)
    serie: Mapped[int] = mapped_column(Integer, default=1)
    chave_acesso: Mapped[Optional[str]] = mapped_column(String(44), unique=True, nullable=True)
    cnpj_emit: Mapped[str] = mapped_column(String(14))
    cnpj_dest: Mapped[str] = mapped_column(String(14))
    valor_total_centavos: Mapped[int] = mapped_column(Integer)
    status: Mapped[StatusNFe] = mapped_column(Enum(StatusNFe), default=StatusNFe.PENDENTE)
    xml_enviado: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    xml_retorno: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    protocolo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    motivo_cancelamento: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    emitido_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
