"""Run one agent turn: Claude tool-use → SoW transitions + executor."""

from __future__ import annotations

import json
import logging
from typing import Any

from anthropic import Anthropic

from config import settings
from executor import AutonomyError, execute_tool
from prompts import AGENT_PROMPTS
from tools import tools_for

log = logging.getLogger("swarmcfo.runtime")


def _client() -> Anthropic | None:
    if not settings.anthropic_api_key:
        return None
    return Anthropic(api_key=settings.anthropic_api_key)


def _block_text(block: Any) -> str:
    """Handle text / thinking content blocks across Claude model versions."""
    btype = getattr(block, "type", None)
    if btype == "text":
        return getattr(block, "text", "") or ""
    if btype == "thinking":
        thinking = getattr(block, "thinking", None)
        return f"[thinking] {thinking}" if thinking else ""
    return ""


async def run_agent(
    agent: str,
    world_snapshot: dict[str, Any],
    user_message: str,
    room_id: str | None = None,
    *,
    sow: Any | None = None,
) -> dict[str, Any]:
    room_id = room_id or settings.demo_room
    if agent not in AGENT_PROMPTS:
        return {"ok": False, "error": f"unknown agent {agent}"}
    system = AGENT_PROMPTS[agent]
    tools = tools_for(agent)
    client = _client()

    if client is None:
        return await _stub_agent(agent, world_snapshot, user_message, room_id, sow=sow)

    message = (
        f"LIVE WORLD SNAPSHOT:\n{json.dumps(world_snapshot, indent=2)[:12000]}\n\n"
        f"EVENT / INSTRUCTION:\n{user_message}\n\n"
        "Use tools for auditable actions. Prefer one clear tool call."
    )

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            system=system,
            tools=tools,
            messages=[{"role": "user", "content": message}],
        )
    except Exception as e:  # noqa: BLE001
        log.exception("claude call failed")
        return {
            "ok": False,
            "agent": agent,
            "error": str(e),
            "text": "",
            "actions": [],
            "model": settings.claude_model,
            "live_claude": False,
        }

    results: list[dict[str, Any]] = []
    text_bits: list[str] = []

    for block in response.content:
        t = _block_text(block)
        if t:
            text_bits.append(t)
        if getattr(block, "type", None) == "tool_use":
            try:
                out = await execute_tool(agent, block.name, block.input, room_id, sow=sow)
                results.append({"tool": block.name, "input": block.input, "result": out})
            except AutonomyError as e:
                results.append({"tool": block.name, "error": str(e), "denied": True})

    return {
        "ok": True,
        "agent": agent,
        "text": "\n".join(text_bits),
        "actions": results,
        "stop_reason": response.stop_reason,
        "model": settings.claude_model,
        "live_claude": True,
        "usage": {
            "input_tokens": getattr(response.usage, "input_tokens", None),
            "output_tokens": getattr(response.usage, "output_tokens", None),
        },
    }


async def _stub_agent(
    agent: str,
    world_snapshot: dict[str, Any],
    user_message: str,
    room_id: str,
    *,
    sow: Any | None = None,
) -> dict[str, Any]:
    """Scripted responses when no API key — keeps demo path alive."""
    _ = world_snapshot
    msg = user_message.lower()
    actions: list[dict[str, Any]] = []

    async def _run(tool: str, payload: dict[str, Any]) -> None:
        actions.append(
            {"tool": tool, "input": payload, "result": await execute_tool(agent, tool, payload, room_id, sow=sow)}
        )

    if agent == "risk" and "duplicate" in msg:
        await _run(
            "block_invoice",
            {
                "invoice_id": "inv-dup-incoming",
                "rationale": "Duplicate: amount+bank+date hash matches inv-dup-original",
                "duplicate_of": "inv-dup-original",
            },
        )
    elif agent == "procurement" and ("spike" in msg or "price" in msg):
        await _run(
            "counter_offer",
            {
                "from_supplier_id": "sup-flour-co",
                "to_supplier_id": "sup-alt-flour",
                "proposed_price_cents": 3800,
                "rationale": "Flour +40%; Coastal Grain Alt — ~$2,728/mo",
                "monthly_savings_cents": 272_800,
            },
        )
    elif agent == "collections" and ("late" in msg or "ar" in msg):
        await _run(
            "chase_ar",
            {
                "receivable_id": "ar-big-cafe",
                "tone": "firm",
                "offer_early_pay_discount_pct": 2.0,
                "rationale": "Harbor Cafe $9,200 at 12 days late — accelerate with 2% early-pay",
            },
        )
    elif agent == "cashier" and ("1400" in msg or "deposit" in msg or "hold" in msg):
        await _run(
            "hold_payment",
            {
                "approval_id": "appr-supplier-deposit",
                "description": "Supplier deposit — North Bay Flour Co",
                "amount_cents": 140_000,
                "rationale": "$1,400 exceeds $1,000 autonomy — waiting for Maya Approve",
            },
        )
    elif agent == "cfo":
        if "disagree" in msg or "arbitrat" in msg:
            await _run(
                "arbitrate",
                {
                    "decision": "use_alt_with_risk_watch",
                    "target_id": "sup-alt-flour",
                    "rationale": "Procurement savings material; Risk trust 0.70 — trial + watchlist",
                },
            )
        await _run(
            "defer_spend",
            {
                "amount_cents": 380_000,
                "rationale": "Defer $3,800 non-critical packaging refresh — runway 11 → ~20 days",
            },
        )

    return {
        "ok": True,
        "agent": agent,
        "text": "(stub — set ANTHROPIC_API_KEY for live Claude)",
        "actions": actions,
        "live_claude": False,
        "model": None,
    }
