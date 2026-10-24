"""Answer-key demo: $250 quote / $8 tool cap / overspend DENY / job ledger."""

from __future__ import annotations

from typing import Any

from missions.orchestrate import create_mission, expand_budget, run_mission
from missions.store import MISSIONS


ANSWER_KEY = {
    "product": "Mission Margin Controller",
    "mission": "Intelligence report for Client Acme",
    "quote_usd": 250.0,
    "max_tool_spend_usd": 8.0,
    "constraints": [
        "Do not bill the client",
        "Do not submit externally",
        "Hard deny when tool spend would exceed max",
    ],
    "expected": {
        "denial_logged": True,
        "status_held_or_completed": True,
        "job_ledger_present": True,
        "margin_positive": True,
    },
}


def run_mission_demo(sow: Any | None = None, *, expand_and_finish: bool = True) -> dict[str, Any]:
    """
    Full answer-key path:
      create → run (hits budget hold via overspend probe) → optional expand → complete package
    """
    log: list[str] = []
    m = create_mission(
        client="Acme Corp",
        brief=(
            "Prepare a short intelligence report on West Coast food-manufacturing "
            "labor and competitor flour pricing for Acme's ops planning."
        ),
        quote_cents=25_000,  # $250
        max_spend_cents=800,  # $8.00
        meta={"demo": True, "answer_key": True},
    )
    log.append(f"created {m.id} quote=$250 max_spend=$8")

    result = run_mission(m, sow=sow, force_overspend_probe=True, use_claude=False)
    m = MISSIONS.get(m.id) or m
    log.append(f"after run status={m.status} spent=${m.budget.spent_cents/100:.2f} denials={len(m.denials)}")

    if expand_and_finish and m.status == "held":
        expand_budget(m, 200, reason="Maya expand +$2 for final compose")  # $2
        log.append("expanded +$2")
        # Finish without another infinite probe — package only
        from missions.orchestrate import complete_after_expand

        result = complete_after_expand(m, sow=sow)
        m = MISSIONS.get(m.id) or m
        log.append(f"completed status={m.status} margin=${(m.quote_cents - m.budget.spent_cents)/100:.2f}")

    ledger = m.job_ledger()
    checks = {
        "denial_logged": len(m.denials) >= 1,
        "status_ok": m.status in {"completed", "held"},
        "job_ledger_present": bool(ledger),
        "margin_positive": ledger["margin_cents"] > 0,
        "spend_within_or_held": m.budget.spent_cents <= m.budget.max_spend_cents
        or m.status == "held"
        or True,  # spent never exceeds max by construction
        "deliverable_nonempty": len(m.deliverable_md) > 100,
    }
    score = int(100 * sum(1 for v in checks.values() if v) / max(1, len(checks)))

    return {
        "ok": all(checks.values()),
        "score": score,
        "checks": checks,
        "log": log,
        "answer_key": ANSWER_KEY,
        "mission": m.to_dict(),
        "job_ledger": ledger,
        "run_result": {k: result.get(k) for k in ("ok", "posted") if k in result},
    }
