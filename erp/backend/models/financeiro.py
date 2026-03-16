from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date, timezone
from typing import Optional
import enum
from core.database import Base


class NaturezaConta(str, enum.Enum):
    ATIVO = "ativo"
    PASSIVO = "passivo"
    PATRIMONIO = "patrimonio"
    RECEITA = "receita"
    DESPESA = "despesa"
    CMV = "cmv"
    RESULTADO_FINANCEIRO = "resultado_financeiro"


class TipoConta(str, enum.Enum):
    SINTETICA = "sintetica"   # agrupadora
    ANALITICA = "analitica"   # recebe lançamentos


class PlanoContas(Base):
    __tablename__ = "plano_contas"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    descricao: Mapped[str] = mapped_column(String(255))
    natureza: Mapped[NaturezaConta] = mapped_column(Enum(NaturezaConta))
    tipo: Mapped[TipoConta] = mapped_column(Enum(TipoConta), default=TipoConta.ANALITICA)
    conta_pai_id: Mapped[Optional[int]] = mapped_column(ForeignKey("plano_contas.id"), nullable=True)
    ativo: Mapped[bool] = mapped_column(default=True)

    conta_pai: Mapped[Optional["PlanoContas"]] = relationship("PlanoContas", remote_side="PlanoContas.id")
    debitos: Mapped[list["Lancamento"]] = relationship("Lancamento", foreign_keys="Lancamento.debito_conta_id", back_populates="conta_debito")
    creditos: Mapped[list["Lancamento"]] = relationship("Lancamento", foreign_keys="Lancamento.credito_conta_id", back_populates="conta_credito")


class Lancamento(Base):
    __tablename__ = "lancamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_competencia: Mapped[date] = mapped_column()
    data_pagamento: Mapped[Optional[date]] = mapped_column(nullable=True)
    historico: Mapped[str] = mapped_column(String(500))
    debito_conta_id: Mapped[int] = mapped_column(ForeignKey("plano_contas.id"))
    credito_conta_id: Mapped[int] = mapped_column(ForeignKey("plano_contas.id"))
    valor_centavos: Mapped[int] = mapped_column(Integer)   # NUNCA float
    centro_custo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conta_debito: Mapped["PlanoContas"] = relationship("PlanoContas", foreign_keys=[debito_conta_id], back_populates="debitos")
    conta_credito: Mapped["PlanoContas"] = relationship("PlanoContas", foreign_keys=[credito_conta_id], back_populates="creditos")
