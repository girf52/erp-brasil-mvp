"""
[🧪 QA Financeiro] Testes do módulo financeiro.
Cobertura obrigatória: partida dobrada, DRE, arredondamento de centavos, virada de exercício.
"""
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from core.database import Base
from models.financeiro import NaturezaConta, TipoConta
from services.financeiro import (
    criar_conta, listar_contas, criar_lancamento,
    listar_lancamentos, calcular_dre, calcular_balancete,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def contas_base(db):
    """Cria plano de contas mínimo para os testes."""
    receita = criar_conta(db, "4.1.001", "Receita de Vendas", NaturezaConta.RECEITA)
    despesa = criar_conta(db, "5.1.001", "Despesas Administrativas", NaturezaConta.DESPESA)
    caixa   = criar_conta(db, "1.1.001", "Caixa", NaturezaConta.ATIVO)
    return {"receita": receita, "despesa": despesa, "caixa": caixa}


# ─── Plano de Contas ──────────────────────────────────────────────────────────

def test_criar_conta_analitica(db):
    conta = criar_conta(db, "1.1.001", "Caixa", NaturezaConta.ATIVO)
    assert conta.id is not None
    assert conta.codigo == "1.1.001"
    assert conta.tipo == TipoConta.ANALITICA


def test_criar_conta_codigo_duplicado(db):
    criar_conta(db, "1.1.001", "Caixa", NaturezaConta.ATIVO)
    with pytest.raises(HTTPException) as exc:
        criar_conta(db, "1.1.001", "Caixa Duplicado", NaturezaConta.ATIVO)
    assert exc.value.status_code == 409


def test_conta_pai_analitica_rejeitada(db):
    """Conta pai deve ser sintética, não analítica."""
    pai = criar_conta(db, "1.1.001", "Caixa", NaturezaConta.ATIVO, TipoConta.ANALITICA)
    with pytest.raises(HTTPException) as exc:
        criar_conta(db, "1.1.002", "Sub", NaturezaConta.ATIVO, conta_pai_id=pai.id)
    assert exc.value.status_code == 422


def test_criar_conta_hierarquica(db):
    pai = criar_conta(db, "1.1", "Ativo Circulante", NaturezaConta.ATIVO, TipoConta.SINTETICA)
    filho = criar_conta(db, "1.1.001", "Caixa", NaturezaConta.ATIVO, conta_pai_id=pai.id)
    assert filho.conta_pai_id == pai.id


# ─── Lançamentos — Partida Dobrada ────────────────────────────────────────────

def test_lancamento_valido(db, contas_base):
    lanc = criar_lancamento(
        db, date(2026, 3, 15), "Venda à vista",
        debito_conta_id=contas_base["caixa"].id,
        credito_conta_id=contas_base["receita"].id,
        valor_centavos=100000,  # R$1.000,00
    )
    assert lanc.id is not None
    assert lanc.valor_centavos == 100000


def test_lancamento_debito_igual_credito_rejeitado(db, contas_base):
    """Regra: débito ≠ crédito."""
    with pytest.raises(HTTPException) as exc:
        criar_lancamento(
            db, date(2026, 3, 15), "Erro partida dupla",
            debito_conta_id=contas_base["caixa"].id,
            credito_conta_id=contas_base["caixa"].id,
            valor_centavos=100000,
        )
    assert exc.value.status_code == 422


def test_lancamento_valor_zero_rejeitado(db, contas_base):
    with pytest.raises(HTTPException) as exc:
        criar_lancamento(
            db, date(2026, 3, 15), "Valor zero",
            debito_conta_id=contas_base["caixa"].id,
            credito_conta_id=contas_base["receita"].id,
            valor_centavos=0,
        )
    assert exc.value.status_code == 422


def test_lancamento_valor_negativo_rejeitado(db, contas_base):
    with pytest.raises(HTTPException) as exc:
        criar_lancamento(
            db, date(2026, 3, 15), "Valor negativo",
            debito_conta_id=contas_base["caixa"].id,
            credito_conta_id=contas_base["receita"].id,
            valor_centavos=-500,
        )
    assert exc.value.status_code == 422


def test_lancamento_conta_sintetica_rejeitada(db):
    """Apenas contas analíticas recebem lançamentos."""
    sintetica = criar_conta(db, "1", "Ativo", NaturezaConta.ATIVO, TipoConta.SINTETICA)
    analitica = criar_conta(db, "1.1.001", "Caixa", NaturezaConta.ATIVO)
    with pytest.raises(HTTPException) as exc:
        criar_lancamento(
            db, date(2026, 3, 15), "Teste sintética",
            debito_conta_id=sintetica.id,
            credito_conta_id=analitica.id,
            valor_centavos=10000,
        )
    assert exc.value.status_code == 422


# ─── Arredondamento em Centavos ───────────────────────────────────────────────

def test_valores_sempre_em_centavos_inteiros(db, contas_base):
    """R$1,00 / 3 = R$0,33 (33 centavos), não float."""
    # 100 centavos / 3 = 33 (int division)
    valor = 100 // 3
    assert valor == 33
    assert isinstance(valor, int)
    lanc = criar_lancamento(
        db, date(2026, 3, 15), "Rateio",
        debito_conta_id=contas_base["despesa"].id,
        credito_conta_id=contas_base["caixa"].id,
        valor_centavos=valor,
    )
    assert lanc.valor_centavos == 33


# ─── Virada de Exercício ──────────────────────────────────────────────────────

def test_lancamento_31_dezembro_aparece_no_ano_correto(db, contas_base):
    criar_lancamento(
        db, date(2025, 12, 31), "Competência 2025",
        debito_conta_id=contas_base["caixa"].id,
        credito_conta_id=contas_base["receita"].id,
        valor_centavos=500000,
    )
    criar_lancamento(
        db, date(2026, 1, 1), "Competência 2026",
        debito_conta_id=contas_base["caixa"].id,
        credito_conta_id=contas_base["receita"].id,
        valor_centavos=200000,
    )
    dre_2025 = calcular_dre(db, date(2025, 1, 1), date(2025, 12, 31))
    dre_2026 = calcular_dre(db, date(2026, 1, 1), date(2026, 12, 31))
    assert dre_2025["receita_bruta_centavos"] == 500000
    assert dre_2026["receita_bruta_centavos"] == 200000


# ─── DRE ─────────────────────────────────────────────────────────────────────

def test_dre_resultado_correto(db, contas_base):
    """Receita - Despesas = Resultado."""
    criar_lancamento(db, date(2026, 3, 1), "Venda",
                     debito_conta_id=contas_base["caixa"].id,
                     credito_conta_id=contas_base["receita"].id,
                     valor_centavos=1000000)  # R$10.000
    criar_lancamento(db, date(2026, 3, 10), "Aluguel",
                     debito_conta_id=contas_base["despesa"].id,
                     credito_conta_id=contas_base["caixa"].id,
                     valor_centavos=300000)   # R$3.000
    dre = calcular_dre(db, date(2026, 3, 1), date(2026, 3, 31))
    assert dre["receita_bruta_centavos"] == 1000000
    assert dre["total_custos_centavos"] == 300000
    assert dre["resultado_liquido_centavos"] == 700000


def test_dre_periodo_vazio(db, contas_base):
    dre = calcular_dre(db, date(2026, 1, 1), date(2026, 1, 31))
    assert dre["resultado_liquido_centavos"] == 0


# ─── Balancete ────────────────────────────────────────────────────────────────

def test_balancete_saldos_corretos(db, contas_base):
    criar_lancamento(db, date(2026, 3, 1), "Venda",
                     debito_conta_id=contas_base["caixa"].id,
                     credito_conta_id=contas_base["receita"].id,
                     valor_centavos=500000)
    balancete = calcular_balancete(db, date(2026, 3, 31))
    caixa_line = next(l for l in balancete if l["conta_id"] == contas_base["caixa"].id)
    assert caixa_line["debitos_centavos"] == 500000
    assert caixa_line["creditos_centavos"] == 0
    assert caixa_line["saldo_centavos"] == 500000
