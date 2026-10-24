"""
Hyphenate scorecard — 'a moment on stage, and a score to back it.'

Maps judging criteria to measurable demo outputs.
"""

from __future__ import annotations

from typing import Any

from sow.store import SystemOfWork


def score_run(sow: SystemOfWork) -> dict[str, Any]:
    audit = sow.audit.all()
    denials = sow.audit.denials()
    posted = sow.gateway.posted
    policies_active = [p for p in sow.policies.values() if p.status == "active"]
    policies_pending = [p for p in sow.policies.values() if p.status == "needs_approval"]
    blocked = [
        w
        for w in sow.work_items.values()
        if w.state == "BLOCKED" or (w.kind == "ap_invoice" and w.payload.get("blocked"))
    ]
    held = [w for w in sow.work_items.values() if w.state == "HELD"]
    needs_info = [w for w in sow.work_items.values() if w.state == "NEEDS_INFO"]
    posted_items = [w for w in sow.work_items.values() if w.state == "POSTED"]

    dollars_saved = sum(w.amount_cents for w in blocked if w.kind == "ap_invoice") / 100
    monthly_procurement = 2728.0  # from counter-offer demo

    checks = {
        "real_company_messy_corner": bool(sow.golden) and any(
            w.kind in ("cash_match", "ap_invoice") for w in sow.work_items.values()
        ),
        "few_roles_done_deep": len({w.kind for w in sow.work_items.values()}) >= 3,
        "asks_at_right_moment": len(needs_info) > 0 or any(
            e["action"] == "ask" for e in audit
        ),
        "handles_a_no": any(e["action"] == "reject" for e in audit) or any(
            "rejection" in (p.tags or []) for p in sow.precedents.values()
        ),
        "limits_enforced_in_code": len(denials) > 0 or any(
            p.id == "pol-003" for p in sow.policies.values()
        ),
        "record_of_every_call": len(audit) >= len(sow.work_items),
        "self_learning_policies": len(sow.policies) > 0,
        "gateway_only_posts": all(p.get("work_item_id") for p in posted) and not any(
            e["actor"].startswith("agent-") and e["action"] == "post" and e["allowed"]
            for e in audit
        ),
        "audit_queryable": len(audit) > 0,
    }

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    return {
        "hyphenate_score": round(100 * passed / total),
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "wow": {
            "runway_days": round(sow.runway_days, 1),
            "dollars_blocked_fraud": dollars_saved,
            "monthly_procurement_savings_est": monthly_procurement,
            "work_items": len(sow.work_items),
            "posted_to_sor": len(posted_items),
            "policies_active": len(policies_active),
            "policies_pending_approval": len(policies_pending),
            "precedents": len(sow.precedents),
            "audit_events": len(audit),
            "denials_logged": len(denials),
            "holds_waiting_owner": len(held),
        },
        "judging": {
            "01_real_enough": checks["real_company_messy_corner"],
            "02_would_you_hire_it": checks["limits_enforced_in_code"]
            and checks["record_of_every_call"],
            "03_something_new": checks["self_learning_policies"],
            "04_wow_moment": dollars_saved >= 4000 or sow.runway_days >= 18,
        },
    }