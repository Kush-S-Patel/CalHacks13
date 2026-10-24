"""
Map Claude tool calls onto System-of-Work transitions (propose / block / hold / ask)
so live agents write the same audited queue as the scripted demo.
"""

from __future__ import annotations

from typing import Any

from sow.models import (
    AI_CASHIER,
    AI_CFO,
    AI_COLLECTIONS,
    AI_PROCUREMENT,
    AI_RISK,
    SYNC,
    Actor,
)
from sow.roles import Denied
from sow.store import SystemOfWork

AGENT_ACTORS: dict[str, Actor] = {
    "risk": AI_RISK,
    "procurement": AI_PROCUREMENT,
    "collections": AI_COLLECTIONS,
    "cashier": AI_CASHIER,
    "cfo": AI_CFO,
}


def apply_tool_to_sow(
    sow: SystemOfWork,
    agent: str,
    tool_name: str,
    tool_input: dict[str, Any],
) -> dict[str, Any]:
    actor = AGENT_ACTORS.get(agent)
    if not actor:
        return {"ok": False, "error": f"unknown agent {agent}"}

    try:
        if tool_name == "block_invoice":
            item = sow.create_work(
                SYNC,
                kind="ap_invoice",
                subject=tool_input.get("invoice_id") or "invoice",
                title=f"Block invoice {tool_input.get('invoice_id')}",
                amount_cents=0,
                evidence=[tool_input.get("invoice_id") or "", tool_input.get("duplicate_of") or ""],
                payload={
                    "blocked": True,
                    "duplicate_of": tool_input.get("duplicate_of"),
                    "vendor": "North Bay Flour Co",
                    "content_hash": "claude-block",
                },
            )
            sow.block(
                item.id,
                actor,
                tool_input.get("rationale") or "blocked",
                patch={"policy_id": "pol-002", "payload": {"blocked": True, "duplicate_of": tool_input.get("duplicate_of")}},
            )
            return {"ok": True, "work_item_id": item.id, "state": item.state, "tool": tool_name}

        if tool_name == "counter_offer":
            item = sow.create_work(
                SYNC,
                kind="procurement",
                subject=tool_input.get("from_supplier_id") or "supplier",
                title="Supplier price spike — counter-offer",
                amount_cents=int(tool_input.get("monthly_savings_cents") or tool_input.get("proposed_price_cents") or 0),
                evidence=[tool_input.get("from_supplier_id") or "", tool_input.get("to_supplier_id") or ""],
                payload={
                    "from": tool_input.get("from_supplier_id"),
                    "to_supplier": tool_input.get("to_supplier_id"),
                    "monthly_savings_cents": tool_input.get("monthly_savings_cents"),
                },
            )
            sow.propose(
                item.id,
                actor,
                patch={
                    "payload": {
                        "counter_offer": True,
                        "to_supplier": tool_input.get("to_supplier_id"),
                        "monthly_savings_cents": tool_input.get("monthly_savings_cents"),
                    }
                },
                reason=tool_input.get("rationale") or "counter-offer",
            )
            return {"ok": True, "work_item_id": item.id, "state": item.state, "tool": tool_name}

        if tool_name == "chase_ar":
            item = sow.create_work(
                SYNC,
                kind="ar_collect",
                subject=tool_input.get("receivable_id") or "ar",
                title="Chase late AR",
                amount_cents=920_000,
                evidence=[tool_input.get("receivable_id") or ""],
                payload={
                    "tone": tool_input.get("tone"),
                    "early_pay_discount_pct": tool_input.get("offer_early_pay_discount_pct"),
                    "customer": "Harbor Cafe Group",
                    "collected": True,
                },
            )
            sow.propose(
                item.id,
                actor,
                patch={"payload": {"tone": tool_input.get("tone"), "collected": True}},
                reason=tool_input.get("rationale") or "chase AR",
            )
            return {"ok": True, "work_item_id": item.id, "state": item.state, "tool": tool_name}

        if tool_name == "hold_payment":
            item = sow.create_work(
                SYNC,
                kind="spend_hold",
                subject=tool_input.get("approval_id") or "hold",
                title=tool_input.get("description") or "Payment hold",
                amount_cents=int(tool_input.get("amount_cents") or 0),
                evidence=[tool_input.get("approval_id") or ""],
                payload={"vendor": "North Bay Flour Co"},
            )
            sow.hold(item.id, actor, tool_input.get("rationale") or "held for owner")
            return {"ok": True, "work_item_id": item.id, "state": item.state, "tool": tool_name}

        if tool_name == "pay":
            item = sow.create_work(
                SYNC,
                kind="spend_hold",
                subject=tool_input.get("target_id") or "pay",
                title="Auto-pay within autonomy",
                amount_cents=int(tool_input.get("amount_cents") or 0),
                evidence=[],
                payload={},
            )
            sow.propose(item.id, actor, patch={}, reason=tool_input.get("rationale") or "pay")
            return {"ok": True, "work_item_id": item.id, "state": item.state, "tool": tool_name}

        if tool_name == "defer_spend":
            item = sow.create_work(
                SYNC,
                kind="forecast",
                subject="runway",
                title="Defer non-critical spend",
                amount_cents=int(tool_input.get("amount_cents") or 0),
                evidence=[],
                payload={"defer_cents": int(tool_input.get("amount_cents") or 0)},
            )
            sow.propose(
                item.id,
                actor,
                patch={"payload": {"defer_cents": int(tool_input.get("amount_cents") or 0)}},
                reason=tool_input.get("rationale") or "defer",
            )
            return {"ok": True, "work_item_id": item.id, "state": item.state, "tool": tool_name}

        if tool_name == "arbitrate":
            # Find open procurement disagreement or create arbitration note
            open_proc = next(
                (w for w in sow.work_items.values() if w.kind == "procurement" and w.state in {"PROPOSED", "NEEDS_INFO"}),
                None,
            )
            if open_proc:
                from sow.transitions import transition

                transition(
                    open_proc,
                    "arbitrate",
                    actor,
                    sow.audit,
                    patch={
                        "answer": tool_input.get("decision"),
                        "payload": {
                            **(open_proc.payload or {}),
                            "arbitration": tool_input.get("decision"),
                            "target_id": tool_input.get("target_id"),
                        },
                    },
                    reason=tool_input.get("rationale") or "CFO arbitration",
                )
                return {"ok": True, "work_item_id": open_proc.id, "state": open_proc.state, "tool": tool_name}
            return {"ok": True, "tool": tool_name, "note": "no open procurement to arbitrate"}

        if tool_name == "recompute_runway":
            return {"ok": True, "tool": tool_name, "runway_days": sow.runway_days}

        return {"ok": False, "error": f"unhandled tool {tool_name}"}
    except Denied as e:
        return {"ok": False, "denied": True, "error": str(e), "tool": tool_name}
