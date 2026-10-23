"""Run one agent turn: Claude tool-use → executor → SpacetimeDB."""

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


async def run_agent(
    agent: str,
    world_snapshot: dict[str, Any],
    user_message: str,
    room_id: str | None = None,
) -> dict[str, Any]:
    room_id = room_id or settings.demo_room
    system = AGENT_PROMPTS[agent]
    tools = tools_for(agent)
    client = _client()

    if client is None:
        # Deterministic stub when no API key — keeps demo path alive
        return await _stub_agent(agent, world_snapshot, user_message, room_id)

    message = (
        f"LIVE WORLD SNAPSHOT:\n{json.dumps(world_snapshot, indent=2)}\n\n"
        f"EVENT / INSTRUCTION:\n{user_message}\n\n"
        "Respond with tool calls only when taking auditable actions."
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        tools=tools,
        messages=[{"role": "user", "content": message}],
    )

    results: list[dict[str, Any]] = []
    text_bits: list[str] = []

    for block in response.content:
        if block.type == "text":
            text_bits.append(block.text)
        elif block.type == "tool_use":
            try:
                out = await execute_tool(agent, block.name, block.input, room_id)
                results.append({"tool": block.name, "input": block.input, "result": out})
            except AutonomyError as e:
                results.append({"tool": block.name, "error": str(e)})

    return {
        "agent": agent,
        "text": "\n".join(text_bits),
        "actions": results,
        "stop_reason": response.stop_reason,
    }


async def _stub_agent(
    agent: str,
    world_snapshot: dict[str, Any],
    user_message: str,
    room_id: str,
) -> dict[str, Any]:
    """Scripted responses mirroring poc/swarmcfo_sim.py for offline demos."""
    _ = world_snapshot
    msg = user_message.lower()
    actions: list[dict[str, Any]] = []

    if agent == "risk" and "duplicate" in msg:
        actions.append(
            await execute_tool(
                agent,
                "block_invoice",
                {
                    "invoice_id": "inv-dup-incoming",
                    "rationale": "Duplicate: amount+bank+date hash matches inv-dup-original",
                    "duplicate_of": "inv-dup-original",
                },
                room_id,
            )
        )
    elif agent == "procurement" and ("spike" in msg or "price" in msg):
        actions.append(
            await execute_tool(
                agent,
                "counter_offer",
                {
                    "from_supplier_id": "sup-flour-co",
                    "to_supplier_id": "sup-alt-flour",
                    "proposed_price_cents": 3800,
                    "rationale": "Flour +40%; Coastal Grain Alt at $38 vs spiked $58.80 — ~$2,728/mo",
                    "monthly_savings_cents": 272_800,
                },
                room_id,
            )
        )
    elif agent == "collections" and ("late" in msg or "ar" in msg):
        actions.append(
            await execute_tool(
                agent,
                "chase_ar",
                {
                    "receivable_id": "ar-big-cafe",
                    "tone": "firm",
                    "offer_early_pay_discount_pct": 2.0,
                    "rationale": "Harbor Cafe $9,200 at 12 days late — accelerate with 2% early-pay",
                },
                room_id,
            )
        )
    elif agent == "cashier" and ("1400" in msg or "deposit" in msg or "hold" in msg):
        actions.append(
            await execute_tool(
                agent,
                "hold_payment",
                {
                    "approval_id": "appr-supplier-deposit",
                    "description": "Supplier deposit — North Bay Flour Co",
                    "amount_cents": 140_000,
                    "rationale": "$1,400 exceeds $1,000 autonomy — waiting for Maya Approve",
                },
                room_id,
            )
        )
    elif agent == "cfo":
        if "disagree" in msg or "arbitrat" in msg:
            actions.append(
                await execute_tool(
                    agent,
                    "arbitrate",
                    {
                        "decision": "use_alt_with_risk_watch",
                        "target_id": "sup-alt-flour",
                        "rationale": "Procurement savings material; Risk trust 0.70 — trial order + watchlist",
                    },
                    room_id,
                )
            )
        actions.append(
            await execute_tool(
                agent,
                "defer_spend",
                {
                    "amount_cents": 380_000,
                    "rationale": "Defer $3,800 non-critical packaging refresh — runway 11 → ~20 days",
                },
                room_id,
            )
        )

    return {"agent": agent, "text": "(stub — set ANTHROPIC_API_KEY for live Claude)", "actions": actions}