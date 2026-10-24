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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Allow `uvicorn main:app` from agents/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import settings
from sow.graphs import build_graphs
from sow.improve import handle_rejection
from sow.models import ACTORS, MAYA
from sow.roles import Denied
from sow.scenario import bootstrap, run_demo
from sow.scoring import score_run
from sow.store import WORLD, SystemOfWork

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("swarmcfo")

app = FastAPI(
    title="SwarmCFO System of Work",
    description="Autonomous finance for a one-person company — Hyphenate track",
    version="0.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Boot golden records + learned policies once
bootstrap(WORLD)


class ActorAction(BaseModel):
    actor_id: str = MAYA.id
    work_item_id: str
    reason: str = ""


class AskBody(ActorAction):
    question: str


class AnswerBody(ActorAction):
    answer: str


class ChaosKind(BaseModel):
    kind: Literal["price_spike", "duplicate_invoice", "late_ar", "short_wire", "full_demo"]
    room_id: str = "maya-bakery"


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "anthropic_configured": bool(settings.anthropic_api_key),
        "work_items": len(WORLD.work_items),
        "policies": len(WORLD.policies),
        "audit_events": len(WORLD.audit),
        "runway_days": round(WORLD.runway_days, 2),
    }


@app.get("/v1/world")
def get_world() -> dict[str, Any]:
    snap = WORLD.snapshot()
    snap["score"] = score_run(WORLD)
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
    """Supply chain, context, and relationship graphs with $ and fraud flags."""
    return build_graphs(WORLD)


@app.post("/v1/work/{work_item_id}/approve")
def approve_work(work_item_id: str, body: ActorAction | None = None) -> dict[str, Any]:
    actor = ACTORS.get((body.actor_id if body else None) or MAYA.id, MAYA)
    try:
        item = WORLD.approve(work_item_id, actor, (body.reason if body else None) or "approved")
        if item.state == "APPROVED":
            WORLD.post(work_item_id)
        return {"item": item.to_dict(), "world": WORLD.snapshot()}
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


@app.post("/v1/work/{work_item_id}/answer")
def answer_work(work_item_id: str, body: AnswerBody) -> dict[str, Any]:
    actor = ACTORS.get(body.actor_id, MAYA)
    try:
        item = WORLD.answer(work_item_id, actor, body.answer)
        return {"item": item.to_dict()}
    except Denied as e:
        raise HTTPException(403, str(e)) from e


@app.post("/v1/demo/run")
def demo_run() -> dict[str, Any]:
    """Reset-ish full answer-key demo into a fresh SoW, then copy metrics."""
    fresh = SystemOfWork()
    result = run_demo(fresh)
    # Replace world state for UI
    WORLD.work_items = fresh.work_items
    WORLD.policies = fresh.policies
    WORLD.precedents = fresh.precedents
    WORLD.golden = fresh.golden
    WORLD.audit = fresh.audit
    WORLD.gateway = fresh.gateway
    WORLD.cash_balance_cents = fresh.cash_balance_cents
    WORLD.daily_burn_cents = fresh.daily_burn_cents
    return {"score": result["score"], "log": result["log"], "answer_key": result["answer_key"]}


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.agent_service_port, reload=True)