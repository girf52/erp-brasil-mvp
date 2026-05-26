"""Parser para a DRE manual da colaboradora (XLSX com abas por mês).

A planilha tem abas nomeadas como "MARÇO-26", "ABRIL-26", etc.
Cada aba tem rótulos na coluna A e valores nas colunas seguintes.
O parser busca por palavras-chave conhecidas e extrai os valores numéricos.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

_MONTH_MAP = {
    "JAN": "01", "FEV": "02", "MAR": "03", "MARÇ": "03",
    "ABR": "04", "MAI": "05", "JUN": "06", "JUL": "07",
    "AGO": "08", "SET": "09", "OUT": "10", "NOV": "11", "DEZ": "12",
    # Variações sem acento
    "MARCO": "03",
}

# Padrões de busca → chave do campo (case-insensitive, sem acentos)
_FIELD_PATTERNS: list[tuple[str, str]] = [
    # Receita
    (r"receita\s*(bruta|total|operacional|l[íi]quida)?", "receita_caixa"),

    # Pessoal
    (r"sal[áa]rios?\b", "salarios"),
    (r"inss\s*(patronal)?", "inss_patronal"),
    (r"fgts\b", "fgts"),
    (r"pr[óo][\s-]*labore\b", "prolabore"),
    (r"aulas?\s*coletivas?", "aulas_coletivas"),
    (r"total\s*pessoal|pessoal\s*total", "pessoal_total"),

    # CAPEX
    (r"parcela\s*(financiamento|empre\w+|equip\w+)?", "capex"),
    (r"financiamento\s*(m[áa]quinas?|equip\w+)?", "capex"),
    (r"capex\b", "capex"),

    # CMV
    (r"cmv\b|custo\s*(das\s*)?mercadorias?\s*vendidas?", "cmv"),
    (r"suplement\w+|produtos?\s*vendidos?", "cmv"),

    # Resultado
    (r"total\s*(de\s*)?despesas?|despesas?\s*total", "despesas_total"),
    (r"resultado\s*(operacional|bruto)", "resultado_operacional"),
    (r"resultado\s*(l[íi]quido|do\s*per[íi]odo|final)", "resultado_liquido"),

    # Saldos bancários
    (r"saldo\s*inicial\s*(ita[uú]|banco|conta)?", "saldo_inicial_itau"),
    (r"saldo\s*(final|encerramento)\s*(ita[uú]|banco|conta)?", "saldo_final_itau"),
    (r"sicoob\b", "saldo_sicoob"),

    # Aportes
    (r"aportes?\b|aporte\s*de\s*capital", "aportes"),
]

# Campos com prioridade quando há múltiplos matches (último match vence para campos genéricos)
_LOW_PRIORITY = {"receita_caixa", "resultado_operacional"}  # podem ter linhas múltiplas; pegar o maior


def _strip_accents(s: str) -> str:
    """Remove acentos de forma simples para comparação."""
    mapping = str.maketrans(
        "áàãâäéèêëíìîïóòõôöúùûüçÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇ",
        "aaaaaaeeeeiiiiooooouuuucAAAAAAAAEEEEIIIIOOOOOUUUUC",
    )
    return s.translate(mapping)


def _parse_amount(val: Any) -> Decimal | None:
    """Converte valor de célula Excel em Decimal."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            d = Decimal(str(val))
            # Ignora valores muito pequenos (provavelmente 0 ou arredondamento)
            if abs(d) < Decimal("0.01"):
                return None
            return abs(d)  # sempre positivo (a DRE da colaboradora usa positivos)
        except InvalidOperation:
            return None
    if isinstance(val, str):
        # Remove R$, pontos de milhar, substitui vírgula decimal
        cleaned = re.sub(r"[R$\s]", "", val)
        cleaned = cleaned.replace(".", "").replace(",", ".")
        # Remove parênteses indicando negativo
        negative = cleaned.startswith("(") and cleaned.endswith(")")
        cleaned = cleaned.strip("()")
        try:
            d = Decimal(cleaned)
            if abs(d) < Decimal("0.01"):
                return None
            return abs(d)  # manter positivo
        except InvalidOperation:
            return None
    return None


def _detect_period(sheet_name: str) -> str | None:
    """Extrai período "YYYY-MM" do nome da aba. Ex: "MARÇO-26" → "2026-03"."""
    name = _strip_accents(sheet_name.upper()).strip()
    # Padrão: MÊS-AA ou MÊS 26 ou MARÇO2026
    pattern = re.match(r"([A-Z]+)[\s\-\/]*(\d{2,4})", name)
    if not pattern:
        return None
    month_str = pattern.group(1)[:3]
    year_str = pattern.group(2)

    month = _MONTH_MAP.get(month_str)
    if not month:
        return None

    year = year_str if len(year_str) == 4 else f"20{year_str}"
    return f"{year}-{month}"


def parse_dre_manual(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Parseia o XLSX da DRE manual.

    Retorna lista de dicts, um por aba/período encontrado:
    {
        "period": "2026-03",
        "receita_caixa": Decimal,
        "salarios": Decimal,
        ...
        "raw_json": str,   # JSON com todos os campos lidos
    }
    """
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("openpyxl não instalado — instale com: pip install openpyxl")

    try:
        from io import BytesIO
        wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    except Exception as exc:
        raise ValueError(f"Não foi possível abrir o XLSX: {exc}")

    results: list[dict] = []

    for sheet_name in wb.sheetnames:
        period = _detect_period(sheet_name)
        if not period:
            # Aba não corresponde a um mês — pular (ex: "Resumo", "Config")
            continue

        ws = wb[sheet_name]
        fields: dict[str, Decimal] = {}
        raw: dict[str, list[dict]] = {}  # label → [{col_idx, value}]

        # Varrer as primeiras 150 linhas e colunas A–H
        for row in ws.iter_rows(min_row=1, max_row=150, min_col=1, max_col=8):
            label_cell = row[0]
            if label_cell.value is None:
                continue

            label_raw = str(label_cell.value).strip()
            label_norm = _strip_accents(label_raw.lower())

            # Buscar qual campo este rótulo representa
            matched_field: str | None = None
            for pattern, field_key in _FIELD_PATTERNS:
                if re.search(pattern, label_norm):
                    matched_field = field_key
                    break

            if not matched_field:
                continue

            # Procurar valor numérico nas colunas B–H desta linha
            amount: Decimal | None = None
            for cell in row[1:]:
                parsed = _parse_amount(cell.value)
                if parsed is not None and parsed > Decimal("0.01"):
                    amount = parsed
                    break  # primeiro valor numérico da linha

            if amount is None:
                continue

            # Registrar no raw
            if matched_field not in raw:
                raw[matched_field] = []
            raw[matched_field].append({"label": label_raw, "value": float(amount)})

            # Para campos com prioridade baixa, manter o MAIOR valor encontrado
            if matched_field in _LOW_PRIORITY:
                if matched_field not in fields or amount > fields[matched_field]:
                    fields[matched_field] = amount
            else:
                # Último match vence (linhas mais abaixo tendem a ser totais)
                fields[matched_field] = amount

        if not fields:
            # Nenhum campo reconhecido nesta aba
            continue

        record: dict[str, Any] = {
            "period": period,
            "filename": filename,
            "raw_json": json.dumps(raw, ensure_ascii=False),
        }

        # Campos opcionais
        optional_keys = [
            "receita_caixa",
            "salarios", "inss_patronal", "fgts", "prolabore", "aulas_coletivas", "pessoal_total",
            "capex", "cmv",
            "despesas_total", "resultado_operacional", "resultado_liquido",
            "saldo_inicial_itau", "saldo_final_itau", "saldo_sicoob",
            "aportes",
        ]
        for k in optional_keys:
            record[k] = fields.get(k)

        results.append(record)

    if not results:
        raise ValueError(
            "Nenhuma aba com período reconhecido encontrada. "
            "Certifique-se de que as abas estejam nomeadas como 'MARÇO-26', 'ABRIL-26', etc."
        )

    return results
