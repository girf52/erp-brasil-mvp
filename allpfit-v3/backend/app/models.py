from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImportSession(Base):
    __tablename__ = "v3_import_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    period_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )


class Receivable(Base):
    __tablename__ = "v3_receivables"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evo_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    member_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    payment_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )


class BankEntry(Base):
    __tablename__ = "v3_bank_entries"

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_bank_entry_source_external_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entry_type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    counterpart_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dre_group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dre_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_stone_mdr: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )


class CategoryRule(Base):
    __tablename__ = "v3_category_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    dre_group: Mapped[str] = mapped_column(String(100), nullable=False)
    dre_label: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )


class ManualDRE(Base):
    """DRE manual importada da planilha da colaboradora — regime de caixa."""

    __tablename__ = "v3_manual_dre"

    __table_args__ = (
        UniqueConstraint("period", name="uq_manual_dre_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period: Mapped[str] = mapped_column(String(7), nullable=False)        # "2026-03"
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    # ── Receita (regime de caixa) ──────────────────────────────────────────
    receita_caixa: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # ── Pessoal ───────────────────────────────────────────────────────────
    salarios: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    inss_patronal: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    fgts: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    prolabore: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    aulas_coletivas: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    pessoal_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # ── CAPEX ─────────────────────────────────────────────────────────────
    capex: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)  # parcela financiamento

    # ── CMV ───────────────────────────────────────────────────────────────
    cmv: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # ── Resultado ─────────────────────────────────────────────────────────
    despesas_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    resultado_operacional: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    resultado_liquido: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # ── Caixa ─────────────────────────────────────────────────────────────
    saldo_inicial_itau: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    saldo_final_itau: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    saldo_sicoob: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    aportes: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # ── Raw data ──────────────────────────────────────────────────────────
    raw_json: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON de todos os campos encontrados
