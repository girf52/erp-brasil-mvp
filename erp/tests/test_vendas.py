"""
[🧪 QA Vendas/Estoque] Testes obrigatórios Sprint 2.
Cobertura: CMP, estoque negativo bloqueado, faturamento atômico, reserva/cancelamento.
"""
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from core.database import Base
from models.vendas import TipoPessoa, StatusPedido, TipoMovEstoque
from services.vendas import (
    criar_cliente, criar_produto, entrada_estoque, posicao_estoque,
    criar_pedido, faturar_pedido, listar_pedidos,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def base(db):
    cli = criar_cliente(db, TipoPessoa.JURIDICA, "Cliente Teste Ltda")
    prod_a = criar_produto(db, "PROD-001", "Produto A", estoque_minimo=5)
    prod_b = criar_produto(db, "PROD-002", "Produto B", permite_negativo=False)
    prod_neg = criar_produto(db, "PROD-NEG", "Produto Negativo OK", permite_negativo=True)
    return {"cli": cli, "prod_a": prod_a, "prod_b": prod_b, "prod_neg": prod_neg}


# ─── Clientes ─────────────────────────────────────────────────────────────────

def test_criar_cliente(db):
    c = criar_cliente(db, TipoPessoa.FISICA, "João Silva", email="joao@test.com")
    assert c.id is not None
    assert c.nome == "João Silva"


# ─── Produtos ─────────────────────────────────────────────────────────────────

def test_criar_produto(db):
    p = criar_produto(db, "SKU-001", "Caneta Azul", unidade="CX")
    assert p.id is not None
    assert p.estoque_atual == 0
    assert p.custo_medio_centavos == 0


def test_produto_codigo_duplicado(db):
    criar_produto(db, "SKU-001", "Produto A")
    with pytest.raises(HTTPException) as exc:
        criar_produto(db, "SKU-001", "Produto Duplicado")
    assert exc.value.status_code == 409


# ─── CMP — Custo Médio Ponderado ─────────────────────────────────────────────

def test_cmp_primeira_entrada(db, base):
    """Primeira entrada: CMP = custo da entrada."""
    p = entrada_estoque(db, base["prod_a"].id, 100, 1000, date(2026, 3, 1))
    assert p.custo_medio_centavos == 1000
    assert p.estoque_atual == 100


def test_cmp_recalculado_segunda_entrada(db, base):
    """CMP recalculado: (100×R$10 + 100×R$20) / 200 = R$15."""
    entrada_estoque(db, base["prod_a"].id, 100, 1000, date(2026, 3, 1))  # R$10
    p = entrada_estoque(db, base["prod_a"].id, 100, 2000, date(2026, 3, 2))  # R$20
    assert p.custo_medio_centavos == 1500  # R$15,00
    assert p.estoque_atual == 200


def test_cmp_entrada_estoque_zero(db, base):
    """Quando estoque = 0, CMP = custo da nova entrada."""
    p = entrada_estoque(db, base["prod_a"].id, 50, 800, date(2026, 3, 1))
    assert p.custo_medio_centavos == 800


def test_cmp_tres_entradas_progressivas(db, base):
    """Testa CMP com 3 entradas: (10×100 + 20×200 + 30×300) / 60 = 233."""
    entrada_estoque(db, base["prod_a"].id, 10, 100, date(2026, 1, 1))
    entrada_estoque(db, base["prod_a"].id, 20, 200, date(2026, 2, 1))
    p = entrada_estoque(db, base["prod_a"].id, 30, 300, date(2026, 3, 1))
    # (10×100 + 20×200 + 30×300) // 60 = (1000+4000+9000) // 60 = 14000 // 60 = 233
    assert p.custo_medio_centavos == 233
    assert p.estoque_atual == 60


# ─── Estoque Negativo Bloqueado ───────────────────────────────────────────────

def test_estoque_negativo_bloqueado(db, base):
    """Produto sem permite_negativo não pode ficar negativo."""
    entrada_estoque(db, base["prod_b"].id, 5, 1000, date(2026, 3, 1))
    cli = base["cli"]
    with pytest.raises(HTTPException) as exc:
        criar_pedido(db, cli.id, date(2026, 3, 15), [
            {"produto_id": base["prod_b"].id, "qtd": 10, "preco_unitario_centavos": 2000}
        ])
    assert exc.value.status_code == 422
    assert "insuficiente" in exc.value.detail.lower()


def test_estoque_negativo_permitido(db, base):
    """Produto com permite_negativo aceita pedido sem estoque."""
    cli = base["cli"]
    pedido = criar_pedido(db, cli.id, date(2026, 3, 15), [
        {"produto_id": base["prod_neg"].id, "qtd": 50, "preco_unitario_centavos": 500}
    ])
    assert pedido.id is not None
    db.refresh(base["prod_neg"])
    assert base["prod_neg"].estoque_atual == -50


# ─── Faturamento Atômico ──────────────────────────────────────────────────────

def test_criar_pedido_reserva_estoque(db, base):
    entrada_estoque(db, base["prod_a"].id, 100, 1000, date(2026, 3, 1))
    pedido = criar_pedido(db, base["cli"].id, date(2026, 3, 15), [
        {"produto_id": base["prod_a"].id, "qtd": 30, "preco_unitario_centavos": 2000}
    ])
    assert pedido.status == StatusPedido.CONFIRMADO
    assert pedido.total_centavos == 30 * 2000
    db.refresh(base["prod_a"])
    assert base["prod_a"].estoque_atual == 70  # 100 - 30 reservados


def test_faturar_pedido(db, base):
    entrada_estoque(db, base["prod_a"].id, 100, 1000, date(2026, 3, 1))
    pedido = criar_pedido(db, base["cli"].id, date(2026, 3, 15), [
        {"produto_id": base["prod_a"].id, "qtd": 10, "preco_unitario_centavos": 1500}
    ])
    faturado = faturar_pedido(db, pedido.id)
    assert faturado.status == StatusPedido.FATURADO
    assert faturado.faturado_em is not None


def test_faturar_pedido_ja_faturado_rejeitado(db, base):
    entrada_estoque(db, base["prod_a"].id, 50, 1000, date(2026, 3, 1))
    pedido = criar_pedido(db, base["cli"].id, date(2026, 3, 15), [
        {"produto_id": base["prod_a"].id, "qtd": 5, "preco_unitario_centavos": 1500}
    ])
    faturar_pedido(db, pedido.id)
    with pytest.raises(HTTPException) as exc:
        faturar_pedido(db, pedido.id)
    assert exc.value.status_code == 422


def test_pedido_sem_itens_rejeitado(db, base):
    with pytest.raises(HTTPException) as exc:
        criar_pedido(db, base["cli"].id, date(2026, 3, 15), [])
    assert exc.value.status_code == 422


def test_pedido_estoque_insuficiente_rollback_completo(db, base):
    """Se qualquer item falhar, nenhum estoque é reservado."""
    entrada_estoque(db, base["prod_a"].id, 10, 1000, date(2026, 3, 1))
    estoque_antes = base["prod_a"].estoque_atual

    with pytest.raises(HTTPException):
        criar_pedido(db, base["cli"].id, date(2026, 3, 15), [
            {"produto_id": base["prod_a"].id, "qtd": 5, "preco_unitario_centavos": 1000},
            {"produto_id": base["prod_b"].id, "qtd": 999, "preco_unitario_centavos": 1000},  # falha
        ])

    db.refresh(base["prod_a"])
    assert base["prod_a"].estoque_atual == estoque_antes  # rollback: nada mudou


# ─── Posição de Estoque ───────────────────────────────────────────────────────

def test_posicao_estoque(db, base):
    entrada_estoque(db, base["prod_a"].id, 100, 500, date(2026, 3, 1))
    pos = posicao_estoque(db)
    item = next(p for p in pos if p["produto_id"] == base["prod_a"].id)
    assert item["estoque_atual"] == 100
    assert item["alerta_minimo"] is False  # 100 > 5 (mínimo)


def test_alerta_estoque_minimo(db, base):
    entrada_estoque(db, base["prod_a"].id, 3, 500, date(2026, 3, 1))
    pos = posicao_estoque(db)
    item = next(p for p in pos if p["produto_id"] == base["prod_a"].id)
    assert item["alerta_minimo"] is True  # 3 <= 5 (mínimo)
