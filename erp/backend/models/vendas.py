from sqlalchemy import String, Integer, ForeignKey, DateTime, Date, Enum, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date, timezone
from typing import Optional
import enum
from core.database import Base


class TipoPessoa(str, enum.Enum):
    FISICA = "fisica"
    JURIDICA = "juridica"


class StatusCliente(str, enum.Enum):
    ATIVO = "ativo"
    INATIVO = "inativo"
    BLOQUEADO = "bloqueado"


class StatusPedido(str, enum.Enum):
    RASCUNHO = "rascunho"
    CONFIRMADO = "confirmado"
    FATURADO = "faturado"
    CANCELADO = "cancelado"


class TipoMovEstoque(str, enum.Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"
    RESERVA = "reserva"
    CANCELAMENTO_RESERVA = "cancelamento_reserva"


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoPessoa] = mapped_column(Enum(TipoPessoa))
    nome: Mapped[str] = mapped_column(String(255), index=True)
    cpf_cnpj_enc: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Fernet encrypted
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telefone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    limite_credito_centavos: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[StatusCliente] = mapped_column(Enum(StatusCliente), default=StatusCliente.ATIVO)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    pedidos: Mapped[list["Pedido"]] = relationship("Pedido", back_populates="cliente")


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    descricao: Mapped[str] = mapped_column(String(255))
    ncm: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    unidade: Mapped[str] = mapped_column(String(6), default="UN")
    custo_medio_centavos: Mapped[int] = mapped_column(Integer, default=0)   # CMP — NUNCA float
    estoque_atual: Mapped[int] = mapped_column(Integer, default=0)          # em unidades inteiras
    estoque_minimo: Mapped[int] = mapped_column(Integer, default=0)
    permite_negativo: Mapped[bool] = mapped_column(Boolean, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    itens: Mapped[list["PedidoItem"]] = relationship("PedidoItem", back_populates="produto")
    movimentacoes: Mapped[list["MovEstoque"]] = relationship("MovEstoque", back_populates="produto")


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    data: Mapped[date] = mapped_column(Date)
    status: Mapped[StatusPedido] = mapped_column(Enum(StatusPedido), default=StatusPedido.RASCUNHO)
    total_centavos: Mapped[int] = mapped_column(Integer, default=0)
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    faturado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    cliente: Mapped["Cliente"] = relationship("Cliente", back_populates="pedidos")
    itens: Mapped[list["PedidoItem"]] = relationship("PedidoItem", back_populates="pedido", cascade="all, delete-orphan")


class PedidoItem(Base):
    __tablename__ = "pedido_itens"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"))
    qtd: Mapped[int] = mapped_column(Integer)
    preco_unitario_centavos: Mapped[int] = mapped_column(Integer)

    pedido: Mapped["Pedido"] = relationship("Pedido", back_populates="itens")
    produto: Mapped["Produto"] = relationship("Produto", back_populates="itens")


class MovEstoque(Base):
    __tablename__ = "mov_estoque"

    id: Mapped[int] = mapped_column(primary_key=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"))
    tipo: Mapped[TipoMovEstoque] = mapped_column(Enum(TipoMovEstoque))
    qtd: Mapped[int] = mapped_column(Integer)
    custo_unitario_centavos: Mapped[int] = mapped_column(Integer, default=0)
    referencia_tipo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "pedido", "nfe", etc.
    referencia_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    data: Mapped[date] = mapped_column(Date)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    produto: Mapped["Produto"] = relationship("Produto", back_populates="movimentacoes")
