"""
SwarmCFO API — system of work façade.

Harness tools are CRUD on work items. Claude (optional) decides;
transition() + can() + gateway execute. Limits live in code.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Allow `uvicorn main:app` from agents/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import settings
from erp.graph_bridge import build_erp_graphs
from erp.ingest import ingest_bytes
from erp.business.store import BIZ
from erp.intake.docile_ingest import ingest_docile_batch, parse_docile_bytes, preview_docile
from erp.intake.docile_parse import fieldtype_catalog
from erp.intake.pipeline import (
    classify_document,
    ingest_fincritical_sample,
    ingest_ocr_json,
    ingest_train_batch,
)
from erp.store import ERP, seed_sample_if_empty
from erp.summary import build_enterprise_summary
from erp.netsuite.adapter import NETSUITE
from claims.corpus import corpus_summary, lookup_nonprofit
from claims.scenario import run_claims_demo
from claims.store import CLAIMS
from missions.orchestrate import complete_after_expand, create_mission, expand_budget, run_mission
from missions.scenario import run_mission_demo
from missions.store import MISSIONS
from nessie.client import get_nessie
from nessie.demo import provision_maya_bakery, snapshot_for_ui, sync_demo_to_nessie
from runtime import run_agent
from sow.improve import handle_rejection
from sow.models import AI_CLAIMS, ACTORS, FINANCE_MANAGER, MAYA
from sow.roles import Denied
from sow.scenario import bootstrap
from sow.scoring import score_run
from sow.store import WORLD, SystemOfWork

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("swarmcfo")

app = FastAPI(
    title="SwarmCFO ERP Suite",
    description="ERP-adjacent autonomous finance — vault, spreadsheet analyzer, system of work",
    version="0.3.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Boot golden records + learned policies + sample ERP sheets once
bootstrap(WORLD)
seed_sample_if_empty()


class ActorAction(BaseModel):
    actor_id: str = MAYA.id
    work_item_id: str | None = None  # path param is source of truth
    reason: str = ""


class AskBody(ActorAction):
    question: str


class AnswerBody(ActorAction):
    answer: str


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "swarmcfo",
        "docs": "/docs",
        "health": "/health",
        "graphs": "/graphs",
        "graphs_api": "/v1/graphs",
        "world": "/v1/world",
        "erp": "/v1/erp",
        "summary": "/v1/erp/summary",
        "upload": "/v1/erp/upload",
        "businesses": "/v1/erp/businesses",
        "docile": "/v1/erp/intake/docile",
        "nessie": "/v1/nessie",
        "netsuite": "/v1/erp/netsuite",
        "agents": "/v1/agents/{agent}/run",
        "missions": "/v1/missions",
        "claims": "/v1/claims",
        "ui": "http://127.0.0.1:3000/suite",
    }


@app.get("/graphs")
def graphs_alias() -> dict[str, Any]:
    """Browser-friendly alias — ERP-merged graphs when vault has data."""
    return build_erp_graphs(WORLD)


class ChaosKind(BaseModel):
    kind: Literal["price_spike", "duplicate_invoice", "late_ar", "short_wire", "full_demo"]
    room_id: str = "maya-bakery"


@app.get("/health")
def health() -> dict[str, Any]:
    nessie = get_nessie()
    return {
        "ok": True,
        "service": "swarmcfo",
        "anthropic_configured": bool(settings.anthropic_api_key),
        "claude_model": settings.claude_model,
        "nessie_configured": nessie.enabled,
        "nessie_marker": "Powered by Capital One Nessie" if nessie.enabled else None,
        "netsuite": NETSUITE.totals(),
        "work_items": len(WORLD.work_items),
        "policies": len(WORLD.policies),
        "audit_events": len(WORLD.audit),
        "runway_days": round(WORLD.runway_days, 2),
        "erp_documents": len(ERP.documents),
        "erp_accounts": len(ERP.accounts),
        "missions": len(MISSIONS.missions),
        "claims": len(CLAIMS.packages),
    }


class AgentRunBody(BaseModel):
    message: str
    room_id: str = Field(default_factory=lambda: settings.demo_room)


@app.post("/v1/agents/{agent}/run")
async def agent_run(agent: str, body: AgentRunBody) -> dict[str, Any]:
    """Live Claude tool-use → SoW transitions (Risk / Procurement / Collections / Cashier / CFO)."""
    result = await run_agent(
        agent,
        WORLD.snapshot(),
        body.message,
        room_id=body.room_id,
        sow=WORLD,
    )
    result["world"] = {
        "runway_days": WORLD.runway_days,
        "work_items": len(WORLD.work_items),
        "open_holds": len([w for w in WORLD.work_items.values() if w.state == "HELD"]),
    }
    return result


@app.get("/v1/erp/netsuite")
def netsuite_snapshot() -> dict[str, Any]:
    return NETSUITE.snapshot()


@app.post("/v1/erp/netsuite/sync-coa")
def netsuite_sync_coa() -> dict[str, Any]:
    return NETSUITE.sync_coa_from_erp()


@app.get("/v1/nessie")
def nessie_status() -> dict[str, Any]:
    snap = snapshot_for_ui()
    if snap.get("used_nessie"):
        ERP.integrations["nessie"] = {
            "status": snap.get("status") or "connected",
            "last_sync": snap.get("last_sync"),
            "marker": snap.get("marker"),
            "docs": "https://api.nessieisreal.com/",
            "account_id": snap.get("account_id"),
        }
        ERP.save()
    return snap


@app.post("/v1/nessie/provision")
def nessie_provision() -> dict[str, Any]:
    result = provision_maya_bakery()
    if result.get("ok"):
        ERP.integrations["nessie"] = {
            "status": "connected",
            "last_sync": result.get("last_sync"),
            "marker": "Powered by Capital One Nessie",
            "docs": "https://api.nessieisreal.com/",
            "account_id": result.get("account_id"),
            "customer_id": result.get("customer_id"),
        }
        ERP.save()
    return result


@app.post("/v1/nessie/sync-demo")
def nessie_sync_demo() -> dict[str, Any]:
    """Push demo cash events to Nessie without re-running the full SoW."""
    return sync_demo_to_nessie()


@app.get("/v1/world")
def get_world() -> dict[str, Any]:
    snap = WORLD.snapshot()
    snap["score"] = score_run(WORLD)
    snap["nessie"] = snapshot_for_ui()
    return snap


@app.get("/v1/audit")
def get_audit(subject: str | None = None) -> dict[str, Any]:
    if subject:
        return {"events": WORLD.audit.for_subject(subject)}
    return {"events": WORLD.audit.all(), "denials": WORLD.audit.denials()}


@app.get("/v1/audit/{subject}")
def audit_why(subject: str) -> dict[str, Any]:
    """Months later, 'why?' is one query."""
    return {"subject": subject, "events": WORLD.audit.for_subject(subject)}


@app.get("/v1/policies")
def list_policies() -> dict[str, Any]:
    return {"policies": [p.to_dict() for p in WORLD.policies.values()]}


@app.get("/v1/score")
def get_score() -> dict[str, Any]:
    return score_run(WORLD)


@app.get("/v1/graphs")
def get_graphs() -> dict[str, Any]:
    """Supply chain / context / relationships — merged with ERP vault when present."""
    return build_erp_graphs(WORLD)


# ─── ERP vault + spreadsheet analyzer ───────────────────────────────────────


@app.get("/v1/erp")
def erp_snapshot() -> dict[str, Any]:
    return ERP.snapshot()


@app.get("/v1/erp/summary")
def erp_summary() -> dict[str, Any]:
    return build_enterprise_summary(WORLD.snapshot())


@app.post("/v1/erp/upload")
async def erp_upload(
    file: UploadFile = File(...),
    kind_hint: str | None = Form(None),
    scan_text: str | None = Form(None),
) -> dict[str, Any]:
    data = await file.read()
    if not data and not scan_text:
        raise HTTPException(400, "empty upload")
    try:
        result = ingest_bytes(
            filename=file.filename or "upload.bin",
            data=data or b"",
            mime=file.content_type or "application/octet-stream",
            kind_hint=kind_hint,
            source="upload",
            scan_text=scan_text,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, str(e)) from e
    return result


@app.post("/v1/erp/scan-text")
async def erp_scan_text(
    text: str = Form(...),
    filename: str = Form("scanned_financial.txt"),
    kind_hint: str = Form("scanned_financial"),
) -> dict[str, Any]:
    """Paste OCR / scanned financial text into the vault and analyze."""
    return ingest_bytes(
        filename=filename,
        data=text.encode("utf-8"),
        mime="text/plain",
        kind_hint=kind_hint,
        source="scan",
        scan_text=text,
    )


@app.post("/v1/erp/seed-samples")
def erp_seed_samples() -> dict[str, Any]:
    before = len(ERP.documents)
    seed_sample_if_empty()
    if len(ERP.documents) == before:
        # force re-seed by ingesting samples again
        from pathlib import Path

        samples = Path(__file__).resolve().parents[1] / "data" / "samples"
        for path in sorted(samples.glob("*.csv")):
            ingest_bytes(
                filename=path.name,
                data=path.read_bytes(),
                mime="text/csv",
                source="sample",
            )
    return {"documents": len(ERP.documents), "snapshot": ERP.snapshot()["totals"]}


@app.delete("/v1/erp/derived")
def erp_clear_derived() -> dict[str, Any]:
    ERP.clear_derived()
    return {"ok": True, "totals": ERP.snapshot()["totals"]}


# ─── Document intake (FinDoc OCR + FinCriticalED) ────────────────────────────


class ClassifyBody(BaseModel):
    text: str = ""
    filename: str = ""
    hinted_class: str | None = None


@app.post("/v1/erp/intake/classify")
def intake_classify(body: ClassifyBody) -> dict[str, Any]:
    return classify_document(text=body.text, filename=body.filename, hinted_class=body.hinted_class)


@app.post("/v1/erp/intake/ocr")
async def intake_ocr(
    file: UploadFile = File(...),
    hinted_class: str | None = Form(None),
) -> dict[str, Any]:
    """Ingest a FinDoc-style OCR JSON ({word, bounding_box}[]) into the ERP vault."""
    data = await file.read()
    try:
        return ingest_ocr_json(
            raw=data,
            filename=file.filename or "ocr.json",
            hinted_class=hinted_class,
            source="upload_ocr",
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, str(e)) from e


@app.post("/v1/erp/intake/train-batch")
def intake_train_batch(
    per_class: int = 3,
    include_fincritical: bool = True,
    fincritical_limit: int = 3,
) -> dict[str, Any]:
    """
    Bulk-index local train_data:
      - daitavan/financial-documents OCR under data/train_data/accounting_samples/...
      - TheFinAI/FinCriticalED rows under data/train_data/scans/raw_input.csv
    """
    return ingest_train_batch(
        per_class=per_class,
        include_fincritical=include_fincritical,
        fincritical_limit=fincritical_limit,
    )


@app.post("/v1/erp/intake/fincritical")
def intake_fincritical(limit: int = 5) -> dict[str, Any]:
    return ingest_fincritical_sample(limit=limit)


# ─── DocILE → per-business enterprise knowledge ─────────────────────────────


@app.get("/v1/erp/intake/docile/preview")
def docile_preview(limit: int = 3) -> dict[str, Any]:
    return preview_docile(limit=limit)


@app.get("/v1/erp/intake/docile/fieldtypes")
def docile_fieldtypes() -> dict[str, Any]:
    return fieldtype_catalog()


@app.post("/v1/erp/intake/docile")
def intake_docile(limit: int = 40) -> dict[str, Any]:
    """
    Bulk-read local DocILE annotations (synthetic / annotated-trainval),
    expand each issuing vendor into a per-business profile (customers,
    line-item supply parties, relationships), and push parties/flows into ERP.
    """
    return ingest_docile_batch(limit=limit)


@app.post("/v1/erp/intake/docile/upload")
async def intake_docile_upload(file: UploadFile = File(...)) -> dict[str, Any]:
    data = await file.read()
    try:
        return parse_docile_bytes(data, filename=file.filename or "annotation.json")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, str(e)) from e


@app.get("/v1/erp/businesses")
def list_businesses() -> dict[str, Any]:
    return {"businesses": BIZ.list_summaries(), "count": len(BIZ.profiles)}


@app.get("/v1/erp/businesses/{biz_id}")
def get_business(biz_id: str) -> dict[str, Any]:
    p = BIZ.get(biz_id)
    if not p:
        raise HTTPException(404, f"unknown business {biz_id}")
    return {"profile": p.to_dict(), "graph": BIZ.graph_for(biz_id)}


@app.get("/v1/erp/businesses/{biz_id}/graph")
def business_graph(biz_id: str) -> dict[str, Any]:
    g = BIZ.graph_for(biz_id)
    if not g:
        raise HTTPException(404, f"unknown business {biz_id}")
    return g


@app.post("/v1/work/{work_item_id}/approve")
def approve_work(work_item_id: str, body: ActorAction | None = None) -> dict[str, Any]:
    default_actor = FINANCE_MANAGER.id if work_item_id else MAYA.id
    raw_actor = (body.actor_id if body else None) or default_actor
    # Claim work defaults to Finance Manager; bakery kinds keep Maya unless specified
    item_peek = WORLD.work_items.get(work_item_id)
    if item_peek and str(item_peek.kind).startswith("claim") and (not body or not body.actor_id):
        raw_actor = FINANCE_MANAGER.id
    actor = ACTORS.get(raw_actor, MAYA)
    try:
        item = WORLD.approve(work_item_id, actor, (body.reason if body else None) or "approved")
        posted = None
        if item.state == "APPROVED":
            # Claims never post to funder / ledger — prepare only
            if str(item.kind).startswith("claim"):
                posted = {"skipped": True, "reason": "claims do not submit or alter ledger"}
            else:
                dest = {
                    "ap_invoice": "netsuite",
                    "cash_match": "netsuite",
                    "ar_collect": "crm",
                    "spend_hold": "nessie",
                    "forecast": "fpa",
                    "procurement": "procurement",
                }.get(item.kind, "netsuite")
                posted = WORLD.post(work_item_id, destination=dest)
        return {"item": item.to_dict(), "posted": posted, "world": WORLD.snapshot(), "netsuite": NETSUITE.totals()}
    except Denied as e:
        raise HTTPException(403, str(e)) from e
    except KeyError as e:
        raise HTTPException(404, f"unknown work item {work_item_id}") from e


@app.post("/v1/work/{work_item_id}/reject")
def reject_work(work_item_id: str, body: ActorAction) -> dict[str, Any]:
    try:
        prec = handle_rejection(WORLD, work_item_id, body.actor_id, body.reason or "rejected")
        return {"precedent": prec.to_dict(), "world": WORLD.snapshot()}
    except Denied as e:
        raise HTTPException(403, str(e)) from e


@app.post("/v1/work/{work_item_id}/ask")
def ask_work(work_item_id: str, body: AskBody) -> dict[str, Any]:
    actor = ACTORS.get(body.actor_id or AI_CLAIMS.id, AI_CLAIMS)
    try:
        item = WORLD.ask(work_item_id, actor, body.question)
        return {"item": item.to_dict(), "world": WORLD.snapshot()}
    except Denied as e:
        raise HTTPException(403, str(e)) from e
    except KeyError as e:
        raise HTTPException(404, f"unknown work item {work_item_id}") from e


@app.post("/v1/work/{work_item_id}/answer")
def answer_work(work_item_id: str, body: AnswerBody) -> dict[str, Any]:
    item_peek = WORLD.work_items.get(work_item_id)
    default = FINANCE_MANAGER.id if item_peek and str(item_peek.kind).startswith("claim") else MAYA.id
    actor = ACTORS.get(body.actor_id or default, MAYA)
    try:
        item = WORLD.answer(work_item_id, actor, body.answer)
        return {"item": item.to_dict(), "world": WORLD.snapshot()}
    except Denied as e:
        raise HTTPException(403, str(e)) from e


@app.post("/v1/demo/run")
def demo_run() -> dict[str, Any]:
    """
    Primary demo = Claims learning loop only (Hyphenate-competitive path).
    Bakery SoW is intentionally not the lead — see /v1/missions/demo for secondary.
    """
    claims = run_claims_demo(WORLD)
    return {
        "product": "SwarmCFO Claims",
        "demo": "learning_loop",
        "score": claims.get("score"),
        "ok": claims.get("ok"),
        "claims": claims,
        "viz": claims.get("viz"),
        "risk": claims.get("risk"),
        "corpus": claims.get("corpus"),
        "results": claims.get("results"),
        "story": claims.get("story"),
        "audit": claims.get("audit"),
        "outcome": claims.get("outcome"),
        "log": list(claims.get("log") or []),
        "answer_key": claims.get("answer_key"),
        "netsuite": NETSUITE.snapshot(),
    }


@app.post("/v1/demo/chaos")
def demo_chaos(body: ChaosKind) -> dict[str, Any]:
    if body.kind == "full_demo":
        return demo_run()
    # Partial chaos: run full demo once (deterministic) if world empty of holds
    if not any(w.kind == "spend_hold" for w in WORLD.work_items.values()):
        return demo_run()
    return {"ok": True, "world": WORLD.snapshot(), "score": score_run(WORLD)}


@app.post("/v1/reset")
def reset_world() -> dict[str, Any]:
    fresh = bootstrap(SystemOfWork())
    WORLD.work_items = fresh.work_items
    WORLD.policies = fresh.policies
    WORLD.precedents = fresh.precedents
    WORLD.golden = fresh.golden
    WORLD.audit = fresh.audit
    WORLD.gateway = fresh.gateway
    WORLD.cash_balance_cents = fresh.cash_balance_cents
    WORLD.daily_burn_cents = fresh.daily_burn_cents
    return WORLD.snapshot()


# ─── Mission Margin Controller ───────────────────────────────────────────────


class MissionCreateBody(BaseModel):
    client: str = "Acme Corp"
    brief: str = "Intelligence report"
    quote_cents: int | None = None
    max_spend_cents: int | None = None


class MissionExpandBody(BaseModel):
    additional_cents: int = 200
    reason: str = "owner expand budget"


@app.get("/v1/missions")
def list_missions() -> dict[str, Any]:
    return {"missions": MISSIONS.list_summaries(), "count": len(MISSIONS.missions)}


@app.post("/v1/missions")
def missions_create(body: MissionCreateBody) -> dict[str, Any]:
    m = create_mission(
        client=body.client,
        brief=body.brief,
        quote_cents=body.quote_cents if body.quote_cents is not None else settings.mission_default_quote_cents,
        max_spend_cents=body.max_spend_cents
        if body.max_spend_cents is not None
        else settings.mission_default_max_spend_cents,
    )
    return {"mission": m.to_dict()}


@app.get("/v1/missions/{mission_id}")
def missions_get(mission_id: str) -> dict[str, Any]:
    m = MISSIONS.get(mission_id)
    if not m:
        raise HTTPException(404, f"unknown mission {mission_id}")
    return {"mission": m.to_dict(), "job_ledger": m.job_ledger()}


@app.post("/v1/missions/{mission_id}/run")
def missions_run(mission_id: str, force_overspend_probe: bool = True) -> dict[str, Any]:
    m = MISSIONS.get(mission_id)
    if not m:
        raise HTTPException(404, f"unknown mission {mission_id}")
    return run_mission(m, sow=WORLD, force_overspend_probe=force_overspend_probe)


@app.post("/v1/missions/{mission_id}/expand-budget")
def missions_expand(mission_id: str, body: MissionExpandBody) -> dict[str, Any]:
    m = MISSIONS.get(mission_id)
    if not m:
        raise HTTPException(404, f"unknown mission {mission_id}")
    expand_budget(m, body.additional_cents, reason=body.reason)
    # Create budget_expand work for audit trail
    from sow.models import SYNC

    wi = WORLD.create_work(
        SYNC,
        kind="budget_expand",  # type: ignore[arg-type]
        subject=mission_id,
        title=f"Expand mission budget +${body.additional_cents/100:.2f}",
        amount_cents=body.additional_cents,
        payload={"mission_id": mission_id, "reason": body.reason},
    )
    m.work_item_ids.append(wi.id)
    MISSIONS.upsert(m)
    finished = complete_after_expand(m, sow=WORLD)
    return finished


@app.post("/v1/missions/demo")
def missions_demo() -> dict[str, Any]:
    """Answer-key: $250 quote / $8 cap / deny overspend / job ledger + margin."""
    return run_mission_demo(WORLD, expand_and_finish=True)


# ─── SwarmCFO Claims (nonprofit reimbursements) ─────────────────────────────


@app.get("/v1/claims")
def list_claims() -> dict[str, Any]:
    return {"claims": CLAIMS.list_summaries(), "count": len(CLAIMS.packages), "corpus": corpus_summary()}


@app.get("/v1/claims/corpus")
def claims_corpus() -> dict[str, Any]:
    return corpus_summary()


@app.get("/v1/claims/nonprofit")
def claims_nonprofit_lookup(q: str | None = None, ein: str | None = None, limit: int = 20) -> dict[str, Any]:
    """
    Enrichment lookup across ProPublica 990 financials, IRS TEOS index, and
    California Grants Portal awards. Awards ≠ reimbursement outcomes.
    """
    if not (q or ein):
        raise HTTPException(400, "provide q and/or ein")
    return lookup_nonprofit(q=q, ein=ein, limit=max(1, min(limit, 50)))


@app.get("/v1/claims/{claim_id}")
def get_claim(claim_id: str) -> dict[str, Any]:
    p = CLAIMS.get(claim_id)
    if not p:
        raise HTTPException(404, f"unknown claim {claim_id}")
    return {"claim": p.to_dict()}


@app.post("/v1/claims/demo")
def claims_demo() -> dict[str, Any]:
    """
    Primary Hyphenate demo: Claims learning loop.
    Rev1 → ask $860 → manager no → rev2 → precedent → policy → next hold →
    agent approve DENIED → finance manager approve. Do not submit / alter ledger.
    """
    return run_claims_demo(WORLD)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.agent_service_port, reload=True)