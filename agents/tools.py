"""Anthropic tool schemas. Claude decides; callers invoke SpacetimeDB reducers."""

from __future__ import annotations

TOOLS_BY_AGENT: dict[str, list[dict]] = {
    "risk": [
        {
            "name": "block_invoice",
            "description": "Block an invoice as duplicate or fraudulent. Records auditable agent_action.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "string"},
                    "rationale": {"type": "string"},
                    "duplicate_of": {"type": "string", "description": "Original invoice id if duplicate"},
                },
                "required": ["invoice_id", "rationale"],
            },
        }
    ],
    "procurement": [
        {
            "name": "counter_offer",
            "description": "Draft/send a counter-offer switching to an alternative supplier after a price spike.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "from_supplier_id": {"type": "string"},
                    "to_supplier_id": {"type": "string"},
                    "proposed_price_cents": {"type": "integer"},
                    "rationale": {"type": "string"},
                    "monthly_savings_cents": {"type": "integer"},
                },
                "required": [
                    "from_supplier_id",
                    "to_supplier_id",
                    "proposed_price_cents",
                    "rationale",
                ],
            },
        }
    ],
    "collections": [
        {
            "name": "chase_ar",
            "description": "Escalate collection on a late receivable with tone-aware messaging.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "receivable_id": {"type": "string"},
                    "tone": {"type": "string", "enum": ["friendly", "firm", "final"]},
                    "offer_early_pay_discount_pct": {"type": "number"},
                    "rationale": {"type": "string"},
                },
                "required": ["receivable_id", "tone", "rationale"],
            },
        }
    ],
    "cashier": [
        {
            "name": "pay",
            "description": "Execute a payment if amount_cents <= autonomy limit ($1000).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "target_id": {"type": "string"},
                    "amount_cents": {"type": "integer"},
                    "rationale": {"type": "string"},
                },
                "required": ["target_id", "amount_cents", "rationale"],
            },
        },
        {
            "name": "hold_payment",
            "description": "Hold a payment above autonomy limit for owner one-tap Approve.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "approval_id": {"type": "string"},
                    "description": {"type": "string"},
                    "amount_cents": {"type": "integer"},
                    "rationale": {"type": "string"},
                },
                "required": ["approval_id", "description", "amount_cents", "rationale"],
            },
        },
    ],
    "cfo": [
        {
            "name": "defer_spend",
            "description": "Defer non-critical spend to extend runway.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "amount_cents": {"type": "integer"},
                    "rationale": {"type": "string"},
                },
                "required": ["amount_cents", "rationale"],
            },
        },
        {
            "name": "arbitrate",
            "description": "Decide when agents disagree (e.g. Procurement vs Risk on a supplier).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string"},
                    "target_id": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["decision", "target_id", "rationale"],
            },
        },
        {
            "name": "recompute_runway",
            "description": "Force runway recomputation after material events.",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
    ],
}


def tools_for(agent: str) -> list[dict]:
    return TOOLS_BY_AGENT.get(agent, [])