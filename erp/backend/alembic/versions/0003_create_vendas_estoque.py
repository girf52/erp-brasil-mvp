"""create vendas e estoque

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("cpf_cnpj_enc", sa.String(500), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("limite_credito_centavos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativo"),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clientes_nome", "clientes", ["nome"])

    op.create_table(
        "produtos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("descricao", sa.String(255), nullable=False),
        sa.Column("ncm", sa.String(8), nullable=True),
        sa.Column("unidade", sa.String(6), nullable=False, server_default="UN"),
        sa.Column("custo_medio_centavos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estoque_atual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estoque_minimo", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("permite_negativo", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_produtos_codigo", "produtos", ["codigo"], unique=True)

    op.create_table(
        "pedidos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="rascunho"),
        sa.Column("total_centavos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("faturado_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pedido_itens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), sa.ForeignKey("pedidos.id"), nullable=False),
        sa.Column("produto_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=False),
        sa.Column("qtd", sa.Integer(), nullable=False),
        sa.Column("preco_unitario_centavos", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "mov_estoque",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("produto_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("qtd", sa.Integer(), nullable=False),
        sa.Column("custo_unitario_centavos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("referencia_tipo", sa.String(50), nullable=True),
        sa.Column("referencia_id", sa.Integer(), nullable=True),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("mov_estoque")
    op.drop_table("pedido_itens")
    op.drop_table("pedidos")
    op.drop_index("ix_produtos_codigo", table_name="produtos")
    op.drop_table("produtos")
    op.drop_index("ix_clientes_nome", table_name="clientes")
    op.drop_table("clientes")
