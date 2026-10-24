"""Hard mission budget — enforced in code, not the prompt."""

from __future__ import annotations

from typing import Any

from missions.models import (
    CLAUDE_INPUT_CENTS_PER_1K,
    CLAUDE_OUTPUT_CENTS_PER_1K,
    TOOL_PRICES_CENTS,
    Mission,
    ToolCharge,
    new_id,
    now_iso,
)


class BudgetDenied(PermissionError):
    def __init__(self, mission_id: str, agent: str, tool: str, amount_cents: int, why: str):
        self.mission_id = mission_id
        self.agent = agent
        self.tool = tool
        self.amount_cents = amount_cents
        self.why = why
        super().__init__(f"BUDGET_DENIED {mission_id} {agent}/{tool} {amount_cents}c: {why}")


def price_tool(tool: str, *, meta: dict[str, Any] | None = None) -> int:
    meta = meta or {}
    if tool == "claude_turn":
        inp = int(meta.get("input_tokens") or 0)
        out = int(meta.get("output_tokens") or 0)
        cents = (inp * CLAUDE_INPUT_CENTS_PER_1K + out * CLAUDE_OUTPUT_CENTS_PER_1K + 999) // 1000
        return max(1, cents) if (inp or out) else TOOL_PRICES_CENTS.get("claude_turn", 1) or 1
    if tool in TOOL_PRICES_CENTS:
        return int(TOOL_PRICES_CENTS[tool])
    # Unknown tools are expensive by default — forces explicit pricing
    return int(meta.get("amount_cents") or 50)


def charge(
    mission: Mission,
    *,
    agent: str,
    tool: str,
    amount_cents: int | None = None,
    meta: dict[str, Any] | None = None,
    near_limit_hold_pct: float = 0.95,
) -> ToolCharge:
    """
    Attempt to debit the mission budget.
    Raises BudgetDenied if remaining < amount (after recording denial).
    """
    meta = dict(meta or {})
    amt = int(amount_cents if amount_cents is not None else price_tool(tool, meta=meta))
    remaining = mission.budget.remaining_cents

    if amt > remaining:
        denial = ToolCharge(
            id=new_id("deny"),
            at=now_iso(),
            agent=agent,
            tool=tool,
            amount_cents=amt,
            allowed=False,
            reason=f"remaining {remaining}c < required {amt}c (max {mission.budget.max_spend_cents}c)",
            meta=meta,
        )
        mission.denials.append(denial)
        mission.charges.append(denial)
        mission.status = "held"
        mission.updated_at = now_iso()
        mission.log.append(f"DENIED {agent}/{tool} {amt}c — {denial.reason}")
        mission.exceptions.append(f"Budget hold: {agent} could not call {tool} (${amt/100:.2f})")
        raise BudgetDenied(mission.id, agent, tool, amt, denial.reason)

    # Soft signal when crossing near-limit threshold (still allow this charge)
    spent_after = mission.budget.spent_cents + amt
    if mission.budget.max_spend_cents > 0:
        ratio = spent_after / mission.budget.max_spend_cents
        if ratio >= near_limit_hold_pct and mission.budget.spent_cents / max(1, mission.budget.max_spend_cents) < near_limit_hold_pct:
            mission.log.append(f"WARN near budget limit after {agent}/{tool} ({ratio:.0%})")

    rec = ToolCharge(
        id=new_id("chg"),
        at=now_iso(),
        agent=agent,
        tool=tool,
        amount_cents=amt,
        allowed=True,
        reason="ok",
        meta=meta,
    )
    mission.budget.spent_cents += amt
    mission.charges.append(rec)
    mission.updated_at = now_iso()
    mission.log.append(f"CHARGE {agent}/{tool} {amt}c · remaining {mission.budget.remaining_cents}c")
    return rec
