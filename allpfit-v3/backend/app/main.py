"""Allp Fit Finance v3 — FastAPI application entry point."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from sqlalchemy import or_
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_session_factory, init_db
from app.engine.categorizer import (
    batch_classify_entries,
    classify_with_rules,
    seed_default_rules,
)
from app.engine.dre import calc_dre
from app.models import BankEntry, CategoryRule, ImportSession, ManualDRE, Receivable
from app.parsers.dre_manual import parse_dre_manual
from app.parsers.evo import parse_evo
from app.parsers.itau import parse_itau
from app.parsers.stone import parse_stone


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with get_session_factory()() as db:
        await seed_default_rules(db)
    yield


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Allp Fit Finance v3", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}


@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    try:
        from sqlalchemy import text

        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@app.get("/dashboard")
async def dashboard(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    df = date_from or date(today.year, today.month, 1)
    dt = date_to or today

    # Import status for each source
    import_status: dict[str, dict] = {}
    for source in ["evo", "stone", "itau"]:
        last_result = await db.execute(
            select(ImportSession)
            .where(ImportSession.source == source)
            .order_by(ImportSession.imported_at.desc())
            .limit(1)
        )
        sess = last_result.scalar_one_or_none()

        if source == "evo":
            total_result = await db.execute(
                select(func.count()).select_from(Receivable)
            )
        else:
            total_result = await db.execute(
                select(func.count()).select_from(BankEntry).where(BankEntry.source == source)
            )

        import_status[source] = {
            "last_import": sess.imported_at.date().isoformat() if sess else None,
            "records": sess.records if sess else 0,
            "filename": sess.filename if sess else None,
        }

    dre_data = await calc_dre(db, df, dt)

    # DRE Manual do período (se existir) — tenta o mês inicial do filtro
    manual_period = f"{df.year}-{df.month:02d}"
    manual_result = await db.execute(
        select(ManualDRE).where(ManualDRE.period == manual_period)
    )
    manual_row = manual_result.scalar_one_or_none()

    def _dec(v) -> float | None:
        return float(v) if v is not None else None

    manual_dre_data = None
    if manual_row:
        manual_dre_data = {
            "period":               manual_row.period,
            "filename":             manual_row.filename,
            "imported_at":          manual_row.imported_at.date().isoformat() if manual_row.imported_at else None,
            "receita_caixa":        _dec(manual_row.receita_caixa),
            "salarios":             _dec(manual_row.salarios),
            "inss_patronal":        _dec(manual_row.inss_patronal),
            "fgts":                 _dec(manual_row.fgts),
            "prolabore":            _dec(manual_row.prolabore),
            "aulas_coletivas":      _dec(manual_row.aulas_coletivas),
            "pessoal_total":        _dec(manual_row.pessoal_total),
            "capex":                _dec(manual_row.capex),
            "cmv":                  _dec(manual_row.cmv),
            "despesas_total":       _dec(manual_row.despesas_total),
            "resultado_operacional": _dec(manual_row.resultado_operacional),
            "resultado_liquido":    _dec(manual_row.resultado_liquido),
            "saldo_inicial_itau":   _dec(manual_row.saldo_inicial_itau),
            "saldo_final_itau":     _dec(manual_row.saldo_final_itau),
            "saldo_sicoob":         _dec(manual_row.saldo_sicoob),
            "aportes":              _dec(manual_row.aportes),
        }

    rules_result = await db.execute(
        select(CategoryRule).order_by(CategoryRule.priority.desc(), CategoryRule.id)
    )
    rules = [
        {
            "id": r.id,
            "keyword": r.keyword,
            "dre_group": r.dre_group,
            "dre_label": r.dre_label,
            "priority": r.priority,
        }
        for r in rules_result.scalars()
    ]

    return {
        **dre_data,
        "import_status": import_status,
        "category_rules": rules,
        "manual_dre": manual_dre_data,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# File import
# ---------------------------------------------------------------------------


@app.post("/import/{source}")
async def import_file(
    source: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Import a file from EVO, Stone or Itaú.

    Uses PostgreSQL batch upsert (INSERT ON CONFLICT) to handle large
    files efficiently within Vercel's 60-second function timeout.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    if source not in ("evo", "stone", "itau", "dre-manual"):
        raise HTTPException(400, "source deve ser evo, stone, itau ou dre-manual")

    file_bytes = await file.read()
    filename = file.filename or f"{source}_import"

    # ── DRE Manual — fluxo separado ─────────────────────────────────────────
    if source == "dre-manual":
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        try:
            dre_records = parse_dre_manual(file_bytes, filename)
        except Exception as exc:
            raise HTTPException(400, f"Erro ao processar planilha DRE: {str(exc)}")
        if not dre_records:
            raise HTTPException(400, "Nenhum período reconhecido na planilha")

        imported_periods = []
        for rec in dre_records:
            row = {
                "id":                   uuid.uuid4(),
                "period":               rec["period"],
                "filename":             filename,
                "receita_caixa":        rec.get("receita_caixa"),
                "salarios":             rec.get("salarios"),
                "inss_patronal":        rec.get("inss_patronal"),
                "fgts":                 rec.get("fgts"),
                "prolabore":            rec.get("prolabore"),
                "aulas_coletivas":      rec.get("aulas_coletivas"),
                "pessoal_total":        rec.get("pessoal_total"),
                "capex":                rec.get("capex"),
                "cmv":                  rec.get("cmv"),
                "despesas_total":       rec.get("despesas_total"),
                "resultado_operacional": rec.get("resultado_operacional"),
                "resultado_liquido":    rec.get("resultado_liquido"),
                "saldo_inicial_itau":   rec.get("saldo_inicial_itau"),
                "saldo_final_itau":     rec.get("saldo_final_itau"),
                "saldo_sicoob":         rec.get("saldo_sicoob"),
                "aportes":              rec.get("aportes"),
                "raw_json":             rec.get("raw_json"),
            }
            stmt = pg_insert(ManualDRE).values([row])
            stmt = stmt.on_conflict_do_update(
                constraint="uq_manual_dre_period",
                set_={k: stmt.excluded[k] for k in row if k != "id"},
            )
            await db.execute(stmt)
            imported_periods.append(rec["period"])

        await db.commit()
        return {
            "source": "dre-manual",
            "imported": len(dre_records),
            "periods": imported_periods,
            "filename": filename,
        }
    # ── fim DRE Manual ──────────────────────────────────────────────────────

    try:
        if source == "evo":
            records, period_from, period_to = parse_evo(file_bytes, filename)
        elif source == "stone":
            records, period_from, period_to = parse_stone(file_bytes, filename)
        else:
            records, period_from, period_to = parse_itau(file_bytes, filename)
    except Exception as exc:
        raise HTTPException(400, f"Erro ao processar arquivo: {str(exc)}")

    if not records:
        raise HTTPException(400, "Nenhum registro encontrado no arquivo")

    try:
        if source == "evo":
            # ── Batch upsert EVO receivables (chunked to stay under 32767 params) ──
            # 9 columns per row → max safe chunk = 3000
            CHUNK = 3000
            # Deduplicate by evo_id — keep last occurrence (most recent data wins)
            seen_evo: dict[str, dict] = {}
            for rec in records:
                seen_evo[str(rec["evo_id"])] = rec
            records_deduped = list(seen_evo.values())

            rows = [
                {
                    "id":             uuid.uuid4(),
                    "evo_id":         str(rec["evo_id"]),
                    "member_name":    rec.get("member_name"),
                    "description":    rec.get("description"),
                    "amount":         rec["amount"],
                    "due_date":       rec["due_date"],
                    "payment_date":   rec.get("payment_date"),
                    "status":         rec.get("status", "open"),
                    "payment_method": rec.get("payment_method"),
                }
                for rec in records_deduped
            ]
            for i in range(0, len(rows), CHUNK):
                chunk = rows[i : i + CHUNK]
                stmt = pg_insert(Receivable).values(chunk)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["evo_id"],
                    set_={
                        "member_name":    stmt.excluded.member_name,
                        "description":    stmt.excluded.description,
                        "amount":         stmt.excluded.amount,
                        "due_date":       stmt.excluded.due_date,
                        "payment_date":   stmt.excluded.payment_date,
                        "status":         stmt.excluded.status,
                        "payment_method": stmt.excluded.payment_method,
                    },
                )
                await db.execute(stmt)
            await db.commit()
            new_count = len(rows)
            updated_count = 0

        else:
            # ── Load rules once for classification ────────────────────────
            rules_result = await db.execute(
                select(CategoryRule).order_by(CategoryRule.priority.desc())
            )
            rules = list(rules_result.scalars())

            # ── Batch upsert BankEntries (chunked to stay under 32767 params) ──
            # 11 columns per row → max safe chunk = 2500
            CHUNK = 2500
            rows = []
            for rec in records:
                desc = rec.get("description") or ""
                # For Itaú entries the beneficiary is in counterpart_name
                # (e.g. "PIX ENVIADO" + "ALLP FIT FRANQUEADORA LTD").
                # Combine both fields so user rules can match on beneficiary name.
                ctpt = rec.get("counterpart_name") or ""
                classify_text = f"{desc} {ctpt}".strip()
                dre_group, dre_label = classify_with_rules(classify_text, rules)
                rows.append({
                    "id":               uuid.uuid4(),
                    "source":           rec.get("source", source),
                    "external_id":      rec.get("external_id"),
                    "entry_type":       rec["entry_type"],
                    "amount":           rec["amount"],
                    "date":             rec["date"],
                    "description":      rec.get("description"),
                    "counterpart_name": rec.get("counterpart_name"),
                    "dre_group":        dre_group,
                    "dre_label":        dre_label,
                    "is_stone_mdr":     rec.get("is_stone_mdr", False),
                })

            for i in range(0, len(rows), CHUNK):
                chunk = rows[i : i + CHUNK]
                stmt = pg_insert(BankEntry).values(chunk)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_bank_entry_source_external_id",
                    set_={
                        "entry_type":       stmt.excluded.entry_type,
                        "amount":           stmt.excluded.amount,
                        "date":             stmt.excluded.date,
                        "description":      stmt.excluded.description,
                        "counterpart_name": stmt.excluded.counterpart_name,
                        "dre_group":        stmt.excluded.dre_group,
                        "dre_label":        stmt.excluded.dre_label,
                        "is_stone_mdr":     stmt.excluded.is_stone_mdr,
                    },
                )
                await db.execute(stmt)
            await db.commit()
            new_count = len(rows)
            updated_count = 0

    except Exception as exc:
        import traceback
        raise HTTPException(500, f"Erro ao salvar no banco: {str(exc)}\n\n{traceback.format_exc()}")

    # Record import session
    db.add(
        ImportSession(
            id=uuid.uuid4(),
            source=source,
            filename=filename,
            period_from=period_from,
            period_to=period_to,
            records=len(records),
        )
    )
    await db.commit()

    return {
        "source":      source,
        "records":     len(records),
        "imported":    new_count,
        "skipped_duplicates": updated_count,
        "errors":      0,
        "period_from": str(period_from) if period_from else None,
        "period_to":   str(period_to) if period_to else None,
    }


# ---------------------------------------------------------------------------
# Category rules CRUD
# ---------------------------------------------------------------------------


class CategoryRuleCreate(BaseModel):
    keyword: str
    dre_group: str
    dre_label: str
    priority: int = 0


@app.post("/category-rules")
async def create_rule(
    body: CategoryRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    rule = CategoryRule(**body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {
        "id": rule.id,
        "keyword": rule.keyword,
        "dre_group": rule.dre_group,
        "dre_label": rule.dre_label,
        "priority": rule.priority,
    }


@app.delete("/category-rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(CategoryRule).where(CategoryRule.id == rule_id))
    await db.commit()
    return {"deleted": True}


@app.put("/reclassify")
async def reclassify(db: AsyncSession = Depends(get_db)):
    count = await batch_classify_entries(db)
    return {"reclassified": count}


# ---------------------------------------------------------------------------
# Bank Entries — list, patch, bulk-classify
# ---------------------------------------------------------------------------


@app.get("/entries")
async def list_entries(
    source: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    entry_type: str | None = Query(None),
    dre_group: str | None = Query(None),
    only_unclassified: bool = Query(False),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List bank entries with pagination and filters."""
    q = select(BankEntry)

    if source:
        q = q.where(BankEntry.source == source)
    if date_from:
        q = q.where(BankEntry.date >= date_from)
    if date_to:
        q = q.where(BankEntry.date <= date_to)
    if entry_type:
        q = q.where(BankEntry.entry_type == entry_type)
    if only_unclassified:
        q = q.where(BankEntry.dre_group == "Outros", BankEntry.dre_label == "Não Classificado")
    elif dre_group:
        q = q.where(BankEntry.dre_group == dre_group)
    if search:
        q = q.where(
            or_(
                BankEntry.description.ilike(f"%{search}%"),
                BankEntry.counterpart_name.ilike(f"%{search}%"),
            )
        )

    total_result = await db.execute(
        select(func.count()).select_from(q.subquery())
    )
    total = total_result.scalar() or 0

    q = q.order_by(BankEntry.date.desc(), BankEntry.id).offset((page - 1) * page_size).limit(page_size)
    rows = list((await db.execute(q)).scalars())

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "entries": [
            {
                "id": str(e.id),
                "source": e.source,
                "entry_type": e.entry_type,
                "amount": float(e.amount),
                "date": str(e.date),
                "description": e.description,
                "counterpart_name": e.counterpart_name,
                "dre_group": e.dre_group,
                "dre_label": e.dre_label,
                "is_stone_mdr": e.is_stone_mdr,
            }
            for e in rows
        ],
    }


class EntryUpdate(BaseModel):
    dre_group: str
    dre_label: str


@app.patch("/entries/{entry_id}")
async def update_entry(
    entry_id: str,
    body: EntryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update dre_group/dre_label for a single entry.

    Returns similar_unclassified — how many other entries with the same
    counterpart_name are still 'Outros / Não Classificado'.
    """
    import uuid as _uuid
    try:
        eid = _uuid.UUID(entry_id)
    except ValueError:
        raise HTTPException(400, "Entry ID inválido")

    entry = (await db.execute(select(BankEntry).where(BankEntry.id == eid))).scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Entry não encontrada")

    entry.dre_group = body.dre_group
    entry.dre_label = body.dre_label
    await db.commit()

    # Count how many other entries with same counterpart_name are unclassified
    similar_count = 0
    if entry.counterpart_name:
        sim_q = select(func.count()).select_from(BankEntry).where(
            BankEntry.counterpart_name == entry.counterpart_name,
            BankEntry.dre_group == "Outros",
            BankEntry.id != eid,
        )
        similar_count = (await db.execute(sim_q)).scalar() or 0

    return {
        "updated": True,
        "entry_id": entry_id,
        "similar_unclassified": similar_count,
        "counterpart_name": entry.counterpart_name,
    }


class BulkClassifyBody(BaseModel):
    counterpart_name: str | None = None
    description_keyword: str | None = None
    dre_group: str
    dre_label: str


@app.post("/entries/bulk-classify")
async def bulk_classify_by_pattern(
    body: BulkClassifyBody,
    db: AsyncSession = Depends(get_db),
):
    """Classify all entries matching counterpart_name or description keyword."""
    if not body.counterpart_name and not body.description_keyword:
        raise HTTPException(400, "Forneça counterpart_name ou description_keyword")

    q = select(BankEntry)
    if body.counterpart_name:
        q = q.where(BankEntry.counterpart_name == body.counterpart_name)
    else:
        q = q.where(BankEntry.description.ilike(f"%{body.description_keyword}%"))

    entries = list((await db.execute(q)).scalars())
    for e in entries:
        e.dre_group = body.dre_group
        e.dre_label = body.dre_label
    if entries:
        await db.commit()

    return {"updated": len(entries)}


# ---------------------------------------------------------------------------
# Aliases /rules → /category-rules (compatibilidade com frontend)
# ---------------------------------------------------------------------------


@app.post("/rules")
async def create_rule_alias(
    body: CategoryRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    return await create_rule(body, db)


@app.delete("/rules/{rule_id}")
async def delete_rule_alias(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await delete_rule(rule_id, db)


# ---------------------------------------------------------------------------
# DRE Manual — consulta da planilha importada
# ---------------------------------------------------------------------------


def _decimal_or_none(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


@app.get("/manual-dre")
async def list_manual_dre(db: AsyncSession = Depends(get_db)):
    """Lista todos os períodos da DRE manual importada."""
    result = await db.execute(
        select(ManualDRE).order_by(ManualDRE.period.desc())
    )
    rows = list(result.scalars())

    def _row_to_dict(r: ManualDRE) -> dict:
        return {
            "period":               r.period,
            "filename":             r.filename,
            "imported_at":          r.imported_at.isoformat() if r.imported_at else None,
            "receita_caixa":        _decimal_or_none(r.receita_caixa),
            "salarios":             _decimal_or_none(r.salarios),
            "inss_patronal":        _decimal_or_none(r.inss_patronal),
            "fgts":                 _decimal_or_none(r.fgts),
            "prolabore":            _decimal_or_none(r.prolabore),
            "aulas_coletivas":      _decimal_or_none(r.aulas_coletivas),
            "pessoal_total":        _decimal_or_none(r.pessoal_total),
            "capex":                _decimal_or_none(r.capex),
            "cmv":                  _decimal_or_none(r.cmv),
            "despesas_total":       _decimal_or_none(r.despesas_total),
            "resultado_operacional": _decimal_or_none(r.resultado_operacional),
            "resultado_liquido":    _decimal_or_none(r.resultado_liquido),
            "saldo_inicial_itau":   _decimal_or_none(r.saldo_inicial_itau),
            "saldo_final_itau":     _decimal_or_none(r.saldo_final_itau),
            "saldo_sicoob":         _decimal_or_none(r.saldo_sicoob),
            "aportes":              _decimal_or_none(r.aportes),
        }

    return {"records": [_row_to_dict(r) for r in rows]}


@app.get("/manual-dre/{period}")
async def get_manual_dre(period: str, db: AsyncSession = Depends(get_db)):
    """Retorna a DRE manual de um período específico (ex: 2026-03)."""
    result = await db.execute(
        select(ManualDRE).where(ManualDRE.period == period)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, f"DRE manual do período {period} não encontrada")

    def _dec(v) -> float | None:
        return float(v) if v is not None else None

    return {
        "period":               row.period,
        "filename":             row.filename,
        "imported_at":          row.imported_at.isoformat() if row.imported_at else None,
        "receita_caixa":        _dec(row.receita_caixa),
        "salarios":             _dec(row.salarios),
        "inss_patronal":        _dec(row.inss_patronal),
        "fgts":                 _dec(row.fgts),
        "prolabore":            _dec(row.prolabore),
        "aulas_coletivas":      _dec(row.aulas_coletivas),
        "pessoal_total":        _dec(row.pessoal_total),
        "capex":                _dec(row.capex),
        "cmv":                  _dec(row.cmv),
        "despesas_total":       _dec(row.despesas_total),
        "resultado_operacional": _dec(row.resultado_operacional),
        "resultado_liquido":    _dec(row.resultado_liquido),
        "saldo_inicial_itau":   _dec(row.saldo_inicial_itau),
        "saldo_final_itau":     _dec(row.saldo_final_itau),
        "saldo_sicoob":         _dec(row.saldo_sicoob),
        "aportes":              _dec(row.aportes),
        "raw_json":             row.raw_json,
    }
