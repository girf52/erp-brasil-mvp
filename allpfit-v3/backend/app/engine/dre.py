"""DRE (Demonstração do Resultado do Exercício) calculation engine.

Revenue:
  - EVO receivables ONLY (Receivable table, status='paid', payment_date in range)
  - Stone BankEntry credits are stored in DB for reference but NOT counted
    as revenue — EVO is the authoritative source to prevent double-counting
    (Stone card transactions ≡ EVO "Cartão Crédito" entries).

MDR:
  - Direct from Stone MDR debit entries (is_stone_mdr=True, entry_type='debit')
  - These are EXCLUDED from the operational expenses section.
  - Stone MDR rates are more accurate than EVO's internal estimate.

Expenses:
  - All debit BankEntries that are NOT Stone MDR entries (typically from Itaú)
  - Grouped by dre_group + dre_label after categorisation
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BankEntry, Receivable


async def calc_dre(db: AsyncSession, date_from: date, date_to: date) -> dict:
    """Calculate the DRE for the given period."""
    today = date.today()

    # -------------------------------------------------------------------------
    # 1a. Receita EVO — recebíveis pagos no período
    # -------------------------------------------------------------------------
    recv_q = await db.execute(
        select(
            Receivable.payment_method,
            func.count().label("qty"),
            func.sum(Receivable.amount).label("total"),
        )
        .where(
            Receivable.status == "paid",
            Receivable.payment_date >= date_from,
            Receivable.payment_date <= date_to,
        )
        .group_by(Receivable.payment_method)
    )
    recv_rows = recv_q.fetchall()

    _METHOD_LABELS: dict[str, str] = {
        "credit":  "Cartão Crédito",
        "debit":   "Cartão Débito",
        "pix":     "PIX / TED",
        "cash":    "Dinheiro",
        "boleto":  "Boleto",
        "other":   "Outros",
    }
    _METHOD_ORDER = ["credit", "debit", "pix", "cash", "boleto", "other"]

    receita_evo = Decimal("0")
    evo_by_method: dict[str, dict] = {}
    for row in recv_rows:
        method = row.payment_method or "other"
        total = Decimal(str(row.total or 0))
        evo_by_method[method] = {
            "label":  _METHOD_LABELS.get(method, method),
            "count":  row.qty,
            "amount": float(total),
        }
        receita_evo += total

    receita_por_tipo: list[dict] = []
    for m in _METHOD_ORDER:
        if m in evo_by_method:
            receita_por_tipo.append(evo_by_method[m])
    for m, d in evo_by_method.items():
        if m not in _METHOD_ORDER:
            receita_por_tipo.append(d)

    # -------------------------------------------------------------------------
    # 1b. Stone créditos — NÃO somados à receita, mas calculados para
    #     exibir no mdr_detail (conferência: Stone deve ≈ EVO Cartão)
    # -------------------------------------------------------------------------
    stone_rev_q = await db.execute(
        select(
            func.count().label("qty"),
            func.coalesce(func.sum(BankEntry.amount), Decimal("0")).label("total"),
        )
        .where(
            BankEntry.source == "stone",
            BankEntry.is_stone_mdr == False,  # noqa: E712
            BankEntry.date >= date_from,
            BankEntry.date <= date_to,
        )
    )
    stone_rev_row = stone_rev_q.fetchone()
    receita_stone = Decimal(str(stone_rev_row.total or 0))
    stone_rev_count = stone_rev_row.qty or 0

    # Stone credits are intentionally excluded from receita_bruta.
    # EVO already covers all revenue; adding Stone would double-count card sales.
    receita_bruta = receita_evo

    # -------------------------------------------------------------------------
    # 2. MDR Stone — débitos marcados is_stone_mdr=True
    # -------------------------------------------------------------------------
    mdr_q = await db.execute(
        select(
            func.count().label("qty"),
            func.coalesce(func.sum(BankEntry.amount), Decimal("0")).label("total"),
        )
        .where(
            BankEntry.is_stone_mdr == True,   # noqa: E712
            BankEntry.entry_type == "debit",
            BankEntry.date >= date_from,
            BankEntry.date <= date_to,
        )
    )
    mdr_row = mdr_q.fetchone()
    mdr_total = Decimal(str(mdr_row.total or 0))
    mdr_count = mdr_row.qty or 0

    # -------------------------------------------------------------------------
    # 3. Despesas — débitos NÃO-MDR, agrupados por dre_group + dre_label
    # "Aplicações Financeiras" (APL APLIC automática) são movimentos de caixa
    # internos, não despesas operacionais — aparecem no breakdown mas NÃO
    # entram em despesas_total nem no resultado.
    # -------------------------------------------------------------------------
    _NON_OPERATIONAL_GROUPS = ("Aplicações Financeiras",)

    desp_q = await db.execute(
        select(
            BankEntry.dre_group,
            BankEntry.dre_label,
            func.count().label("qty"),
            func.sum(BankEntry.amount).label("total"),
        )
        .where(
            BankEntry.entry_type == "debit",
            BankEntry.is_stone_mdr == False,   # noqa: E712 — MDR shown separately
            BankEntry.date >= date_from,
            BankEntry.date <= date_to,
        )
        .group_by(BankEntry.dre_group, BankEntry.dre_label)
        .order_by(func.sum(BankEntry.amount).desc())
    )
    desp_rows = desp_q.fetchall()

    despesas_detalhe: list[dict] = []
    despesas_por_grupo_map: dict[str, dict] = {}
    despesas_total   = Decimal("0")   # operational only (excl. non-operational groups)
    movimentos_capital = Decimal("0") # financial applications etc.

    all_rows = list(desp_rows)
    for row in all_rows:
        grp = row.dre_group or "Outros"
        lbl = row.dre_label or "Não Classificado"
        total = Decimal(str(row.total or 0))
        despesas_detalhe.append(
            {"group": grp, "label": lbl, "count": row.qty, "amount": float(total)}
        )
        if grp not in despesas_por_grupo_map:
            despesas_por_grupo_map[grp] = {"group": grp, "count": 0, "amount": 0.0}
        despesas_por_grupo_map[grp]["count"] += row.qty
        despesas_por_grupo_map[grp]["amount"] += float(total)

        if grp in _NON_OPERATIONAL_GROUPS:
            movimentos_capital += total
        else:
            despesas_total += total

    despesas_por_grupo = sorted(
        list(despesas_por_grupo_map.values()),
        key=lambda x: x["amount"],
        reverse=True,
    )

    # -------------------------------------------------------------------------
    # 4. Fluxo de Caixa — entradas e saídas por fonte (regime de caixa)
    # -------------------------------------------------------------------------

    # Itaú entradas operacionais (créditos — excluindo APL APLIC retornos que
    # são apenas movimentos internos de caixa, não receitas reais)
    itau_in_q = await db.execute(
        select(
            func.coalesce(func.sum(BankEntry.amount), Decimal("0")).label("total"),
            func.count().label("qty"),
        )
        .where(
            BankEntry.source == "itau",
            BankEntry.entry_type == "credit",
            BankEntry.dre_group != "Aplicações Financeiras",
            BankEntry.date >= date_from,
            BankEntry.date <= date_to,
        )
    )
    itau_in_row = itau_in_q.fetchone()
    itau_entradas = Decimal(str(itau_in_row.total or 0))
    itau_entradas_qty = itau_in_row.qty or 0

    # Itaú saídas operacionais (débitos, excluindo MDR e Aplicações Financeiras)
    itau_out_q = await db.execute(
        select(
            func.coalesce(func.sum(BankEntry.amount), Decimal("0")).label("total"),
            func.count().label("qty"),
        )
        .where(
            BankEntry.source == "itau",
            BankEntry.entry_type == "debit",
            BankEntry.is_stone_mdr == False,   # noqa: E712
            BankEntry.dre_group != "Aplicações Financeiras",
            BankEntry.date >= date_from,
            BankEntry.date <= date_to,
        )
    )
    itau_out_row = itau_out_q.fetchone()
    itau_saidas = Decimal(str(itau_out_row.total or 0))
    itau_saidas_qty = itau_out_row.qty or 0

    # Créditos financeiros recebidos (empréstimos MMX etc.)
    fin_in_q = await db.execute(
        select(
            func.coalesce(func.sum(BankEntry.amount), Decimal("0")).label("total"),
        )
        .where(
            BankEntry.entry_type == "credit",
            BankEntry.dre_group == "Financeiro",
            BankEntry.date >= date_from,
            BankEntry.date <= date_to,
        )
    )
    financeiro_recebido = Decimal(str(fin_in_q.fetchone().total or 0))

    # ── Stone: diferença EVO vs caixa ─────────────────────────────────────
    # Receita EVO Cartão (competência) vs Stone créditos (caixa)
    evo_cartao = sum(
        Decimal(str(d["amount"]))
        for d in evo_by_method.values()
        if d["label"] in ("Cartão Crédito", "Cartão Débito")
    )
    stone_vs_evo_diff = receita_stone - evo_cartao  # positivo = Stone > EVO (raro); negativo = inadimplência/pendente

    # ── Lançamentos não classificados (apenas débitos — créditos Stone/Itaú
    #    são tratados pelo EVO e não precisam de categorização para o DRE)
    unclass_q = await db.execute(
        select(
            func.count().label("qty"),
            func.coalesce(func.sum(BankEntry.amount), Decimal("0")).label("total"),
        )
        .where(
            BankEntry.date >= date_from,
            BankEntry.date <= date_to,
            BankEntry.entry_type == "debit",
            BankEntry.is_stone_mdr == False,   # noqa: E712 — MDR tem tratamento próprio
            BankEntry.dre_group == "Outros",
            BankEntry.dre_label == "Não Classificado",
        )
    )
    unclass_row = unclass_q.fetchone()
    unclassified_count = unclass_row.qty or 0
    unclassified_amount = Decimal(str(unclass_row.total or 0))

    # -------------------------------------------------------------------------
    # 5. Inadimplência — recebíveis com vencimento no período (EVO)
    # -------------------------------------------------------------------------
    inadimp_q = await db.execute(
        select(Receivable).where(
            Receivable.due_date >= date_from,
            Receivable.due_date <= date_to,
        )
    )
    inadimp_rows = list(inadimp_q.scalars())

    paid_count   = 0
    open_count   = 0
    overdue_count = 0
    paid_amount   = Decimal("0")
    open_amount   = Decimal("0")
    overdue_amount = Decimal("0")
    total_count   = len(inadimp_rows)

    for rec in inadimp_rows:
        amt = Decimal(str(rec.amount or 0))
        if rec.status == "paid":
            paid_count += 1
            paid_amount += amt
        elif rec.due_date < today:
            overdue_count += 1
            overdue_amount += amt
        else:
            open_count += 1
            open_amount += amt

    # -------------------------------------------------------------------------
    # 6. KPIs
    # -------------------------------------------------------------------------
    receita_liquida = receita_bruta - mdr_total
    resultado       = receita_liquida - despesas_total
    margem = float(resultado / receita_bruta * 100) if receita_bruta > 0 else 0.0

    return {
        "period": {
            "from": str(date_from),
            "to":   str(date_to),
        },
        "kpis": {
            "receita_bruta":        float(receita_bruta),
            "mdr_estimado":         float(mdr_total),    # campo mantido por compatibilidade
            "receita_liquida":      float(receita_liquida),
            "despesas_total":       float(despesas_total),       # operacional (excl. aplicações)
            "movimentos_capital":   float(movimentos_capital),   # APL APLIC etc.
            "resultado":            float(resultado),
            "margem_resultado_pct": round(margem, 2),
        },
        "dre": {
            "receita_por_tipo":    receita_por_tipo,
            "mdr_detail": {
                "evo_receita_total":   float(receita_evo),
                "stone_credits_total": float(receita_stone),
                "stone_credits_count": stone_rev_count,
                "mdr_entries":         mdr_count,
                "mdr_total":           float(mdr_total),
                "evo_cartao_total":    float(evo_cartao),
                "stone_vs_evo_diff":   float(stone_vs_evo_diff),
            },
            "despesas_por_grupo":  despesas_por_grupo,
            "despesas_detalhe":    despesas_detalhe,
            "evo_inadimplencia": {
                "total":          total_count,
                "paid":           paid_count,
                "open":           open_count,
                "overdue":        overdue_count,
                "paid_amount":    float(paid_amount),
                "open_amount":    float(open_amount),
                "overdue_amount": float(overdue_amount),
            },
        },
        "fluxo_caixa": {
            "itau_entradas":        float(itau_entradas),
            "itau_entradas_qty":    itau_entradas_qty,
            "itau_saidas":          float(itau_saidas),
            "itau_saidas_qty":      itau_saidas_qty,
            "itau_liquido":         float(itau_entradas - itau_saidas),
            "stone_recebido":       float(receita_stone),
            "financeiro_recebido":  float(financeiro_recebido),
        },
        "qualidade_dados": {
            "unclassified_count":  unclassified_count,
            "unclassified_amount": float(unclassified_amount),
        },
    }
