"""
Testes Sprint 4 — Módulo RH / Folha
Cobertura: INSS progressivo, IRRF com dependentes, FGTS, holerite
"""
import pytest
import sys
import os

# Injeta paths para importar services diretamente
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

from services.rh import calcular_inss, calcular_irrf, calcular_fgts


# ── Testes unitários de cálculo ──

class TestCalculoINSS:
    """INSS progressivo 2026 — tabela embutida."""

    def test_salario_minimo(self):
        """Salário R$1.412,00 → INSS = 7,5% = R$105,90"""
        inss = calcular_inss(141200)
        assert inss == 10590

    def test_segunda_faixa(self):
        """Salário R$2.000,00 → faixa1(1412*7.5%) + faixa2((2000-1412)*9%)"""
        inss = calcular_inss(200000)
        # faixa1: 141200 * 0.075 = 10590
        # faixa2: (200000-141200) * 0.09 = 58800 * 0.09 = 5292
        assert inss == 10590 + 5292

    def test_terceira_faixa(self):
        """Salário R$3.500,00"""
        inss = calcular_inss(350000)
        # faixa1: 141200 * 0.075 = 10590
        # faixa2: (282400-141200) * 0.09 = 141200 * 0.09 = 12708
        # faixa3: (350000-282400) * 0.12 = 67600 * 0.12 = 8112
        assert inss == 10590 + 12708 + 8112

    def test_teto_inss(self):
        """Salário R$10.000,00 → para no teto de R$7.500,00"""
        inss_10k = calcular_inss(1000000)
        inss_teto = calcular_inss(750000)
        assert inss_10k == inss_teto  # Acima do teto, mesmo valor

    def test_salario_zero(self):
        assert calcular_inss(0) == 0


class TestCalculoIRRF:
    """IRRF com deduções por dependente."""

    def test_isento(self):
        """Salário baixo → IRRF = 0 (isento)"""
        # Salário R$2.000 - INSS ~R$159 = base ~R$1.841 < R$2.000,96
        inss = calcular_inss(200000)
        irrf = calcular_irrf(200000, inss, 0)
        assert irrf == 0

    def test_com_dependentes_reduz_irrf(self):
        """Dependentes reduzem base de cálculo → menos IRRF"""
        inss = calcular_inss(500000)
        irrf_sem = calcular_irrf(500000, inss, 0)
        irrf_com = calcular_irrf(500000, inss, 2)
        assert irrf_com < irrf_sem

    def test_muitos_dependentes_isenta(self):
        """Muitos dependentes → base negativa → IRRF = 0"""
        inss = calcular_inss(300000)
        irrf = calcular_irrf(300000, inss, 10)
        assert irrf == 0

    def test_salario_alto(self):
        """Salário R$10.000 → cai na faixa 27,5%"""
        inss = calcular_inss(1000000)
        irrf = calcular_irrf(1000000, inss, 0)
        assert irrf > 0
        # Base = 1000000 - inss = ~953k → faixa 27.5%
        base = 1000000 - inss
        esperado = round(base * 0.275) - 90131
        assert irrf == esperado


class TestCalculoFGTS:
    """FGTS = 8% do bruto."""

    def test_fgts_padrao(self):
        assert calcular_fgts(500000) == 40000

    def test_fgts_zero(self):
        assert calcular_fgts(0) == 0


# ── Testes de integração via API ──

BASE = "http://localhost:8000"


class TestFuncionariosAPI:

    def test_criar_funcionario(self, client, auth_headers):
        resp = client.post(f"{BASE}/api/rh/funcionarios", headers=auth_headers, json={
            "nome": "Test Worker", "cpf": "11122233344",
            "cargo": "Dev", "salario_base_centavos": 500000,
            "data_admissao": "2025-01-01", "regime": "clt", "dependentes": 0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["nome"] == "Test Worker"
        assert data["status"] == "ativo"

    def test_cpf_duplicado_rejeita(self, client, auth_headers):
        payload = {
            "nome": "Dup Worker", "cpf": "55566677788",
            "cargo": "Dev", "salario_base_centavos": 300000,
            "data_admissao": "2025-01-01", "regime": "clt", "dependentes": 0,
        }
        client.post(f"{BASE}/api/rh/funcionarios", headers=auth_headers, json=payload)
        r2 = client.post(f"{BASE}/api/rh/funcionarios", headers=auth_headers, json=payload)
        assert r2.status_code == 409

    def test_cpf_invalido_rejeita(self, client, auth_headers):
        resp = client.post(f"{BASE}/api/rh/funcionarios", headers=auth_headers, json={
            "nome": "Bad CPF", "cpf": "123",
            "cargo": "Dev", "salario_base_centavos": 300000,
            "data_admissao": "2025-01-01", "regime": "clt", "dependentes": 0,
        })
        assert resp.status_code == 422

    def test_demitir_funcionario(self, client, auth_headers):
        r = client.post(f"{BASE}/api/rh/funcionarios", headers=auth_headers, json={
            "nome": "To Fire", "cpf": "99988877766",
            "cargo": "Dev", "salario_base_centavos": 300000,
            "data_admissao": "2025-01-01", "regime": "clt", "dependentes": 0,
        })
        func_id = r.json()["id"]
        r2 = client.post(f"{BASE}/api/rh/funcionarios/{func_id}/demitir", headers=auth_headers, json={
            "data_demissao": "2026-03-15",
        })
        assert r2.status_code == 200
        assert r2.json()["status"] == "demitido"


class TestFolhaAPI:

    def test_calcular_folha(self, client, auth_headers):
        # Cria funcionário
        client.post(f"{BASE}/api/rh/funcionarios", headers=auth_headers, json={
            "nome": "Folha Test", "cpf": "44433322211",
            "cargo": "Analista", "salario_base_centavos": 350000,
            "data_admissao": "2025-01-01", "regime": "clt", "dependentes": 1,
        })
        # Calcula folha
        resp = client.post(f"{BASE}/api/rh/folha/calcular?competencia=2026-02", headers=auth_headers)
        assert resp.status_code == 200
        folhas = resp.json()
        assert len(folhas) >= 1
        f = folhas[0]
        assert f["salario_bruto"] > 0
        assert f["inss"] > 0
        assert f["fgts"] > 0
        assert f["salario_liquido"] > 0
        assert f["salario_liquido"] < f["salario_bruto"]

    def test_holerite(self, client, auth_headers):
        # Busca folha existente
        resp = client.get(f"{BASE}/api/rh/folha?competencia=2026-03", headers=auth_headers)
        if resp.json():
            folha_id = resp.json()[0]["id"]
            r = client.get(f"{BASE}/api/rh/folha/{folha_id}/holerite", headers=auth_headers)
            assert r.status_code == 200
            h = r.json()
            assert "funcionario" in h
            assert "salario_bruto" in h
            assert "salario_liquido" in h
            assert "eventos" in h

    def test_folha_idempotente(self, client, auth_headers):
        """Calcular folha duas vezes na mesma competência não duplica."""
        client.post(f"{BASE}/api/rh/folha/calcular?competencia=2026-01", headers=auth_headers)
        r1 = client.get(f"{BASE}/api/rh/folha?competencia=2026-01", headers=auth_headers)
        client.post(f"{BASE}/api/rh/folha/calcular?competencia=2026-01", headers=auth_headers)
        r2 = client.get(f"{BASE}/api/rh/folha?competencia=2026-01", headers=auth_headers)
        assert len(r1.json()) == len(r2.json())
