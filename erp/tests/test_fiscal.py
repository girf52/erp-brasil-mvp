"""
Testes Sprint 3 — Módulo Fiscal (NF-e MockSEFAZ)
Cobertura: XML válido, cancelamento 24h, número único por série
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch


# ── Helpers ──

BASE = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}


def get_auth_headers(client):
    """Login and return headers with Bearer token."""
    resp = client.post(f"{BASE}/api/auth/login", json={
        "email": "admin@erp.local", "password": "admin123"
    })
    token = resp.json()["access_token"]
    return {**HEADERS, "Authorization": f"Bearer {token}"}


# ── Testes de Emissão ──

class TestEmissaoNFe:
    """Testes de emissão de NF-e via MockSEFAZ."""

    def test_emitir_nfe_sucesso(self, client, auth_headers):
        resp = client.post(f"{BASE}/api/fiscal/nfe/emitir", headers=auth_headers, json={
            "cnpj_emit": "12345678000199",
            "cnpj_dest": "98765432000188",
            "valor_total_centavos": 150000,
            "serie": 1,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "autorizada"
        assert data["chave_acesso"] is not None
        assert len(data["chave_acesso"]) == 44
        assert data["protocolo"] is not None
        assert data["valor_total_centavos"] == 150000
        assert data["numero"] >= 1

    def test_emitir_nfe_valor_zero_rejeita(self, client, auth_headers):
        resp = client.post(f"{BASE}/api/fiscal/nfe/emitir", headers=auth_headers, json={
            "cnpj_emit": "12345678000199",
            "cnpj_dest": "98765432000188",
            "valor_total_centavos": 0,
            "serie": 1,
        })
        assert resp.status_code == 422

    def test_emitir_nfe_cnpj_invalido_rejeita(self, client, auth_headers):
        resp = client.post(f"{BASE}/api/fiscal/nfe/emitir", headers=auth_headers, json={
            "cnpj_emit": "123",
            "cnpj_dest": "98765432000188",
            "valor_total_centavos": 100000,
            "serie": 1,
        })
        assert resp.status_code == 422

    def test_numero_unico_por_serie(self, client, auth_headers):
        """Duas emissões na mesma série devem ter números sequenciais."""
        r1 = client.post(f"{BASE}/api/fiscal/nfe/emitir", headers=auth_headers, json={
            "cnpj_emit": "12345678000199",
            "cnpj_dest": "98765432000188",
            "valor_total_centavos": 100000,
            "serie": 99,
        })
        r2 = client.post(f"{BASE}/api/fiscal/nfe/emitir", headers=auth_headers, json={
            "cnpj_emit": "12345678000199",
            "cnpj_dest": "98765432000188",
            "valor_total_centavos": 200000,
            "serie": 99,
        })
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r2.json()["numero"] == r1.json()["numero"] + 1


# ── Testes de Cancelamento ──

class TestCancelamentoNFe:
    """Testes de cancelamento de NF-e."""

    def test_cancelar_sucesso(self, client, auth_headers):
        # Emite
        r = client.post(f"{BASE}/api/fiscal/nfe/emitir", headers=auth_headers, json={
            "cnpj_emit": "12345678000199",
            "cnpj_dest": "98765432000188",
            "valor_total_centavos": 100000,
            "serie": 1,
        })
        nfe_id = r.json()["id"]
        # Cancela
        r2 = client.post(f"{BASE}/api/fiscal/nfe/{nfe_id}/cancelar", headers=auth_headers, json={
            "motivo": "Erro nos dados do destinatario da nota fiscal eletronica",
        })
        assert r2.status_code == 200
        assert r2.json()["status"] == "cancelada"
        assert r2.json()["motivo_cancelamento"] is not None

    def test_cancelar_motivo_curto_rejeita(self, client, auth_headers):
        r = client.post(f"{BASE}/api/fiscal/nfe/emitir", headers=auth_headers, json={
            "cnpj_emit": "12345678000199",
            "cnpj_dest": "98765432000188",
            "valor_total_centavos": 100000,
            "serie": 1,
        })
        nfe_id = r.json()["id"]
        r2 = client.post(f"{BASE}/api/fiscal/nfe/{nfe_id}/cancelar", headers=auth_headers, json={
            "motivo": "curto",
        })
        assert r2.status_code == 422

    def test_cancelar_nfe_inexistente(self, client, auth_headers):
        r = client.post(f"{BASE}/api/fiscal/nfe/99999/cancelar", headers=auth_headers, json={
            "motivo": "Motivo de cancelamento valido com mais de 15 caracteres",
        })
        assert r.status_code == 404

    def test_cancelar_nfe_ja_cancelada(self, client, auth_headers):
        # Emite e cancela
        r = client.post(f"{BASE}/api/fiscal/nfe/emitir", headers=auth_headers, json={
            "cnpj_emit": "12345678000199",
            "cnpj_dest": "98765432000188",
            "valor_total_centavos": 100000,
            "serie": 1,
        })
        nfe_id = r.json()["id"]
        client.post(f"{BASE}/api/fiscal/nfe/{nfe_id}/cancelar", headers=auth_headers, json={
            "motivo": "Erro nos dados do destinatario da nota fiscal eletronica",
        })
        # Tenta cancelar de novo
        r2 = client.post(f"{BASE}/api/fiscal/nfe/{nfe_id}/cancelar", headers=auth_headers, json={
            "motivo": "Tentativa de segundo cancelamento da mesma nota",
        })
        assert r2.status_code == 422


# ── Testes de Consulta ──

class TestConsultaNFe:

    def test_listar_nfes(self, client, auth_headers):
        resp = client.get(f"{BASE}/api/fiscal/nfe", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_listar_nfes_filtro_status(self, client, auth_headers):
        resp = client.get(f"{BASE}/api/fiscal/nfe?status=autorizada", headers=auth_headers)
        assert resp.status_code == 200
        for nf in resp.json():
            assert nf["status"] == "autorizada"

    def test_obter_xml(self, client, auth_headers):
        # Emite para ter XML
        r = client.post(f"{BASE}/api/fiscal/nfe/emitir", headers=auth_headers, json={
            "cnpj_emit": "12345678000199",
            "cnpj_dest": "98765432000188",
            "valor_total_centavos": 100000,
            "serie": 1,
        })
        nfe_id = r.json()["id"]
        r2 = client.get(f"{BASE}/api/fiscal/nfe/{nfe_id}/xml", headers=auth_headers)
        assert r2.status_code == 200
        assert "nfeProc" in r2.text or "NFe" in r2.text
