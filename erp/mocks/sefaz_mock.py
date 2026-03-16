"""
MockSEFAZ — Simula a SEFAZ para desenvolvimento sem custo.
Retorna dados realistas mas sintéticos. NUNCA chama API externa real.
"""
import hashlib
import random
from datetime import datetime, timezone


class MockSEFAZ:
    """Simula a SEFAZ para desenvolvimento sem custo."""

    def _gerar_chave_acesso(self) -> str:
        """Gera chave de acesso de 44 dígitos (formato NFe)."""
        # cUF(2) + AAMM(4) + CNPJ(14) + mod(2) + serie(3) + nNF(9) + tpEmis(1) + cNF(8) + cDV(1) = 44
        agora = datetime.now(timezone.utc)
        partes = [
            "35",                                          # SP
            agora.strftime("%y%m"),                        # AAMM
            "00000000000191",                              # CNPJ emit (mock)
            "55",                                          # mod = NF-e
            "001",                                         # série
            str(random.randint(1, 999999999)).zfill(9),    # nNF
            "1",                                           # tpEmis = normal
            str(random.randint(10000000, 99999999)),       # cNF
        ]
        sem_dv = "".join(partes)                           # 43 dígitos
        # Dígito verificador simplificado (mod 11)
        dv = sum(int(d) for d in sem_dv) % 11
        dv = 0 if dv < 2 else 11 - dv
        return sem_dv + str(dv)

    def _assinar_mock(self, xml: str, chave: str) -> str:
        """Simula assinatura XML — adiciona protocolo de autorização."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S-03:00")
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  {xml}
  <protNFe versao="4.00">
    <infProt>
      <tpAmb>2</tpAmb>
      <verAplic>MOCK_SEFAZ_1.0</verAplic>
      <chNFe>{chave}</chNFe>
      <dhRecbto>{ts}</dhRecbto>
      <nProt>3{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}00001</nProt>
      <digVal>{hashlib.sha1(xml.encode()).hexdigest()}</digVal>
      <cStat>100</cStat>
      <xMotivo>Autorizado o uso da NF-e</xMotivo>
    </infProt>
  </protNFe>
</nfeProc>"""

    def autorizar_nfe(self, xml: str) -> dict:
        """Autoriza NF-e (mock) — sempre retorna sucesso."""
        chave = self._gerar_chave_acesso()
        protocolo = f"3{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}00001"
        return {
            "status": "100",
            "motivo": "Autorizado o uso da NF-e",
            "chave_acesso": chave,
            "protocolo": protocolo,
            "xml_protocolo": self._assinar_mock(xml, chave),
        }

    def cancelar_nfe(self, chave: str, motivo: str) -> dict:
        """Cancela NF-e (mock) — sempre retorna sucesso."""
        return {
            "status": "135",
            "motivo": "Evento registrado e vinculado a NF-e",
            "chave_acesso": chave,
            "protocolo": f"3{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}00002",
        }

    def consultar_status(self, chave: str) -> dict:
        """Consulta status (mock) — sempre autorizada."""
        return {
            "status": "100",
            "motivo": "Autorizado o uso da NF-e",
            "chave_acesso": chave,
        }
