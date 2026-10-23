"""SwarmCFO agent service — FastAPI façade over five Claude agents."""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from executor import ACTION_LOG
from runtime import run_agent

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("swarmcfo")

AgentName = Literal["cfo", "risk", "procurement", "collections", "cashier"]

app = FastAPI(title="SwarmCFO Agents", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class WorldSnapshot(BaseModel):
    cash_balance_cents: int = 1_840_000
    daily_burn_cents: int = 165_000
    runway_days: float = 11.15
    invoices: list[dict[str, Any]] = Field(default_factory=list)
    suppliers: list[dict[str, Any]] = Field(default_factory=list)
    receivables: list[dict[str, Any]] = Field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = Field(default_factory=list)


class AgentRequest(BaseModel):
    agent: AgentName
    message: str
    world: WorldSnapshot = Field(default_factory=WorldSnapshot)
    room_id: str = "maya-bakery"


class ChaosRequest(BaseModel):
    """Fan out the three judge chaos events to the right agents."""

    kinds: list[Literal["price_spike", "duplicate_invoice", "late_ar"]] = Field(
        default_factory=lambda: ["price_spike", "duplicate_invoice", "late_ar"]
    )
    room_id: str = "maya-bakery"
    world: WorldSnapshot = Field(default_factory=WorldSnapshot)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "anthropic_configured": bool(settings.anthropic_api_key),
        "autonomy_limit_usd": settings.cashier_auto_pay_limit_usd,
    }


@app.post("/v1/agent/run")
async def agent_run(body: AgentRequest) -> dict[str, Any]:
    try:
        return await run_agent(body.agent, body.world.model_dump(), body.message, body.room_id)
    except KeyError as e:
        raise HTTPException(400, f"unknown agent: {e}") from e


@app.post("/v1/demo/chaos")
async def demo_chaos(body: ChaosRequest) -> dict[str, Any]:
    """Run the prize-demo fan-out: Risk / Procurement / Collections / Cashier / CFO."""
    results: list[dict[str, Any]] = []
    world = body.world.model_dump()

    mapping = {
        "duplicate_invoice": ("risk", "Duplicate $4,200 invoice arrived — vet and block if duplicate."),
        "price_spike": (
            "procurement",
            "Flour supplier raised prices 40%. Find alternative and send counter-offer.",
        ),
        "late_ar": (
            "collections",
            "Harbor Cafe is 12 days late on $9,200 AR. Chase with firm tone + early-pay incentive.",
        ),
    }

    for kind in body.kinds:
        agent, msg = mapping[kind]
        results.append(await run_agent(agent, world, msg, body.room_id))

    # Visible disagreement scene
    results.append(
        await run_agent(
            "cfo",
            world,
            "Procurement wants cheap alt flour; Risk distrusts trust_score 0.70. Arbitrate, then defer $3800 non-critical spend and recompute runway.",
            body.room_id,
        )
    )

    # Cashier hold for owner Approve
    results.append(
        await run_agent(
            "cashier",
            world,
            "Supplier deposit $1,400 due now — hold if above autonomy.",
            body.room_id,
        )
    )

    return {"room_id": body.room_id, "results": results, "action_log": ACTION_LOG[-20:]}


@app.get("/v1/actions")
def list_actions() -> dict[str, Any]:
    return {"actions": ACTION_LOG[-100:]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.agent_service_port, reload=True)