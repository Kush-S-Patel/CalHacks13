"""Execute agent tool calls against SpacetimeDB reducers (or in-memory demo bus)."""

from __future__ import annotations

import logging
from typing import Any

from config import settings

log = logging.getLogger("swarmcfo.executor")

# In-memory action log used when SpacetimeDB is offline (fallback / unit demos)
ACTION_LOG: list[dict[str, Any]] = []


class AutonomyError(Exception):
    pass


def _cents_to_usd(cents: int) -> float:
    return cents / 100.0


async def call_reducer(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """
    Placeholder for SpacetimeDB HTTP / SDK reducer call.
    Wire to generated bindings once `npm run spacetime:generate` is run.
    """
    record = {"reducer": name, "args": args}
    ACTION_LOG.append(record)
    log.info("reducer %s %s", name, args)
    # TODO: POST to SpacetimeDB client when online
    _ = settings.spacetimedb_uri
    return {"ok": True, "reducer": name}


async def execute_tool(agent: str, tool_name: str, tool_input: dict[str, Any], room_id: str) -> dict[str, Any]:
    limit = settings.cashier_auto_pay_limit_usd

    if tool_name == "pay":
        amount = int(tool_input["amount_cents"])
        if _cents_to_usd(amount) > limit:
            raise AutonomyError(
                f"Cashier cannot auto-pay ${_cents_to_usd(amount):.2f}; "
                f"limit is ${limit:.0f}. Use hold_payment."
            )
        return await call_reducer(
            "pay",
            {
                "room_id": room_id,
                "target_id": tool_input["target_id"],
                "amount_cents": amount,
                "agent": agent,
                "rationale": tool_input["rationale"],
            },
        )

    if tool_name == "hold_payment":
        return await call_reducer(
            "hold_payment",
            {
                "room_id": room_id,
                "approval_id": tool_input["approval_id"],
                "description": tool_input["description"],
                "amount_cents": int(tool_input["amount_cents"]),
                "agent": agent,
                "rationale": tool_input["rationale"],
            },
        )

    if tool_name == "block_invoice":
        return await call_reducer(
            "block_invoice",
            {
                "room_id": room_id,
                "invoice_id": tool_input["invoice_id"],
                "agent": agent,
                "rationale": tool_input["rationale"],
                "duplicate_of": tool_input.get("duplicate_of"),
            },
        )

    if tool_name == "counter_offer":
        return await call_reducer(
            "counter_offer",
            {
                "room_id": room_id,
                "from_supplier_id": tool_input["from_supplier_id"],
                "to_supplier_id": tool_input["to_supplier_id"],
                "agent": agent,
                "rationale": tool_input["rationale"],
                "proposed_price_cents": int(tool_input["proposed_price_cents"]),
            },
        )

    if tool_name == "chase_ar":
        return await call_reducer(
            "chase_ar",
            {
                "room_id": room_id,
                "receivable_id": tool_input["receivable_id"],
                "agent": agent,
                "rationale": tool_input["rationale"],
            },
        )

    if tool_name == "defer_spend":
        return await call_reducer(
            "defer_spend",
            {
                "room_id": room_id,
                "amount_cents": int(tool_input["amount_cents"]),
                "agent": agent,
                "rationale": tool_input["rationale"],
            },
        )

    if tool_name == "arbitrate":
        return await call_reducer(
            "arbitrate",
            {
                "room_id": room_id,
                "decision": tool_input["decision"],
                "target_id": tool_input["target_id"],
                "rationale": tool_input["rationale"],
            },
        )

    if tool_name == "recompute_runway":
        return await call_reducer("recompute_runway", {"room_id": room_id})

    return {"ok": False, "error": f"unknown tool {tool_name}"}