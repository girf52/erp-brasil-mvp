"""create plano_contas e lancamentos

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plano_contas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("descricao", sa.String(255), nullable=False),
        sa.Column("natureza", sa.String(30), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="analitica"),
        sa.Column("conta_pai_id", sa.Integer(), sa.ForeignKey("plano_contas.id"), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plano_contas_codigo", "plano_contas", ["codigo"], unique=True)

    op.create_table(
        "lancamentos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("data_competencia", sa.Date(), nullable=False),
        sa.Column("data_pagamento", sa.Date(), nullable=True),
        sa.Column("historico", sa.String(500), nullable=False),
        sa.Column("debito_conta_id", sa.Integer(), sa.ForeignKey("plano_contas.id"), nullable=False),
        sa.Column("credito_conta_id", sa.Integer(), sa.ForeignKey("plano_contas.id"), nullable=False),
        sa.Column("valor_centavos", sa.Integer(), nullable=False),
        sa.Column("centro_custo", sa.String(100), nullable=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lancamentos_data_competencia", "lancamentos", ["data_competencia"])


def downgrade() -> None:
    op.drop_index("ix_lancamentos_data_competencia", table_name="lancamentos")
    op.drop_table("lancamentos")
    op.drop_index("ix_plano_contas_codigo", table_name="plano_contas")
    op.drop_table("plano_contas")
