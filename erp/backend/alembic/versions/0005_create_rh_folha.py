"""create rh/folha tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "funcionarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("cpf", sa.String(11), nullable=False),
        sa.Column("cargo", sa.String(100), nullable=False),
        sa.Column("salario_base_centavos", sa.Integer(), nullable=False),
        sa.Column("data_admissao", sa.Date(), nullable=False),
        sa.Column("data_demissao", sa.Date(), nullable=True),
        sa.Column("regime", sa.String(20), nullable=False, server_default="clt"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativo"),
        sa.Column("dependentes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_funcionarios_cpf", "funcionarios", ["cpf"], unique=True)

    op.create_table(
        "eventos_folha",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("funcionario_id", sa.Integer(), nullable=False),
        sa.Column("competencia", sa.String(7), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("valor_centavos", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eventos_folha_func", "eventos_folha", ["funcionario_id"])

    op.create_table(
        "folhas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("competencia", sa.String(7), nullable=False),
        sa.Column("funcionario_id", sa.Integer(), nullable=False),
        sa.Column("salario_bruto", sa.Integer(), nullable=False),
        sa.Column("inss", sa.Integer(), nullable=False),
        sa.Column("irrf", sa.Integer(), nullable=False),
        sa.Column("fgts", sa.Integer(), nullable=False),
        sa.Column("outros_descontos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("salario_liquido", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="calculada"),
        sa.Column("calculado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_folhas_comp_func", "folhas", ["competencia", "funcionario_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_folhas_comp_func", table_name="folhas")
    op.drop_table("folhas")
    op.drop_index("ix_eventos_folha_func", table_name="eventos_folha")
    op.drop_table("eventos_folha")
    op.drop_index("ix_funcionarios_cpf", table_name="funcionarios")
    op.drop_table("funcionarios")
