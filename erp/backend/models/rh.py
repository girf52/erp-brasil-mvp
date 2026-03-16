from sqlalchemy import String, Integer, DateTime, Date, Enum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date, timezone
from typing import Optional
import enum
from core.database import Base


class RegimeContratacao(str, enum.Enum):
    CLT = "clt"
    PJ = "pj"
    ESTAGIO = "estagio"


class StatusFuncionario(str, enum.Enum):
    ATIVO = "ativo"
    AFASTADO = "afastado"
    DEMITIDO = "demitido"


class StatusFolha(str, enum.Enum):
    CALCULADA = "calculada"
    APROVADA = "aprovada"
    PAGA = "paga"


class TipoEvento(str, enum.Enum):
    HORA_EXTRA = "hora_extra"
    FALTA = "falta"
    BONUS = "bonus"
    DESCONTO = "desconto"
    VALE_TRANSPORTE = "vale_transporte"
    VALE_REFEICAO = "vale_refeicao"


class Funcionario(Base):
    __tablename__ = "funcionarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    cpf: Mapped[str] = mapped_column(String(11), unique=True)
    cargo: Mapped[str] = mapped_column(String(100))
    salario_base_centavos: Mapped[int] = mapped_column(Integer)
    data_admissao: Mapped[date] = mapped_column(Date)
    data_demissao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    regime: Mapped[RegimeContratacao] = mapped_column(Enum(RegimeContratacao), default=RegimeContratacao.CLT)
    status: Mapped[StatusFuncionario] = mapped_column(Enum(StatusFuncionario), default=StatusFuncionario.ATIVO)
    dependentes: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EventoFolha(Base):
    __tablename__ = "eventos_folha"

    id: Mapped[int] = mapped_column(primary_key=True)
    funcionario_id: Mapped[int] = mapped_column(Integer, index=True)
    competencia: Mapped[str] = mapped_column(String(7))  # "2026-03"
    tipo: Mapped[TipoEvento] = mapped_column(Enum(TipoEvento))
    valor_centavos: Mapped[int] = mapped_column(Integer)
    descricao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)


class Folha(Base):
    __tablename__ = "folhas"

    id: Mapped[int] = mapped_column(primary_key=True)
    competencia: Mapped[str] = mapped_column(String(7))  # "2026-03"
    funcionario_id: Mapped[int] = mapped_column(Integer, index=True)
    salario_bruto: Mapped[int] = mapped_column(Integer)  # centavos
    inss: Mapped[int] = mapped_column(Integer)
    irrf: Mapped[int] = mapped_column(Integer)
    fgts: Mapped[int] = mapped_column(Integer)
    outros_descontos: Mapped[int] = mapped_column(Integer, default=0)
    salario_liquido: Mapped[int] = mapped_column(Integer)
    status: Mapped[StatusFolha] = mapped_column(Enum(StatusFolha), default=StatusFolha.CALCULADA)
    calculado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
