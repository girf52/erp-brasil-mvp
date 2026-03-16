"""create notas_fiscais

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notas_fiscais",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("serie", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("chave_acesso", sa.String(44), nullable=True),
        sa.Column("cnpj_emit", sa.String(14), nullable=False),
        sa.Column("cnpj_dest", sa.String(14), nullable=False),
        sa.Column("valor_total_centavos", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("xml_enviado", sa.Text(), nullable=True),
        sa.Column("xml_retorno", sa.Text(), nullable=True),
        sa.Column("protocolo", sa.String(50), nullable=True),
        sa.Column("motivo_cancelamento", sa.String(255), nullable=True),
        sa.Column("emitido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notas_fiscais_numero", "notas_fiscais", ["numero"])
    op.create_index("ix_notas_fiscais_chave", "notas_fiscais", ["chave_acesso"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_notas_fiscais_chave", table_name="notas_fiscais")
    op.drop_index("ix_notas_fiscais_numero", table_name="notas_fiscais")
    op.drop_table("notas_fiscais")
