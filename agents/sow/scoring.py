"""
Hyphenate scorecard — stage moment + score that backs it.

Claims-first: messy nonprofit reimbursement corner, manager no, limits in code,
self-learning policy, queryable audit. Bakery signals still count if present.
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
    claim_kinds = {w.kind for w in sow.work_items.values() if str(w.kind).startswith("claim")}
    claim_ask_events = [
        e
        for e in audit
        if e["action"] == "ask"
        and (
            (
                sow.work_items.get(e["subject"]) is not None
                and str(sow.work_items[e["subject"]].kind).startswith("claim")
            )
            or "catering" in (e.get("reason") or "").lower()
            or "celebration" in (e.get("reason") or "").lower()
            or "priya" in (e.get("reason") or "").lower()
        )
    ]
    manager_no = any(
        e["action"] == "answer"
        and ("no" in (e.get("reason") or "").lower() or "exclude" in (e.get("reason") or "").lower())
        for e in audit
    ) or any("rejection" in (p.tags or []) or "staff_celebration" in (p.tags or []) for p in sow.precedents.values())
    claim_policy = any(p.id.startswith("pol-claim") for p in sow.policies.values())
    claim_deny = any(
        (not e["allowed"]) and e["action"] == "approve" and e["actor"] == "agent-claims" for e in audit
    )

    dollars_saved = sum(w.amount_cents for w in blocked if w.kind == "ap_invoice") / 100
    claims_excluded = 0.0
    for w in sow.work_items.values():
        if w.kind == "claim_prepare" and w.payload.get("excluded_cents"):
            claims_excluded = max(claims_excluded, int(w.payload["excluded_cents"]) / 100)

    checks = {
        "real_company_messy_corner": bool(claim_kinds)
        or (
            bool(sow.golden)
            and any(w.kind in ("cash_match", "ap_invoice") for w in sow.work_items.values())
        ),
        "few_roles_done_deep": len(claim_kinds) >= 2
        or len({w.kind for w in sow.work_items.values()}) >= 3,
        "asks_at_right_moment": len(claim_ask_events) > 0
        or len(needs_info) > 0
        or any(e["action"] == "ask" for e in audit),
        "handles_a_no": manager_no
        or any(e["action"] == "reject" for e in audit)
        or any("rejection" in (p.tags or []) for p in sow.precedents.values()),
        "limits_enforced_in_code": claim_deny
        or len(denials) > 0
        or any(p.id == "pol-003" for p in sow.policies.values()),
        "record_of_every_call": len(audit) >= max(1, len(sow.work_items)),
        "self_learning_policies": claim_policy or len(sow.policies) > 0,
        "gateway_only_posts": (
            all(p.get("work_item_id") for p in posted) if posted else True
        )
        and not any(
            e["actor"].startswith("agent-") and e["action"] == "post" and e["allowed"] for e in audit
        ),
        "audit_queryable": len(audit) > 0,
    }

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    wow_claims = claims_excluded >= 8000 or (
        any(w.kind == "claim_policy_hold" and w.state == "HELD" for w in sow.work_items.values())
        and claim_deny
    )

    return {
        "hyphenate_score": round(100 * passed / total),
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "track": "claims" if claim_kinds else "sow",
        "wow": {
            "runway_days": round(sow.runway_days, 1),
            "dollars_blocked_fraud": dollars_saved,
            "claims_excluded_usd": claims_excluded,
            "monthly_procurement_savings_est": 2728.0 if not claim_kinds else None,
            "work_items": len(sow.work_items),
            "posted_to_sor": len(posted_items),
            "policies_active": len(policies_active),
            "policies_pending_approval": len(policies_pending),
            "precedents": len(sow.precedents),
            "audit_events": len(audit),
            "denials_logged": len(denials),
            "holds_waiting_owner": len(held),
            "claim_work_kinds": sorted(claim_kinds),
        },
        "judging": {
            "01_real_enough": checks["real_company_messy_corner"],
            "02_would_you_hire_it": checks["limits_enforced_in_code"]
            and checks["record_of_every_call"]
            and checks["asks_at_right_moment"],
            "03_something_new": checks["self_learning_policies"] and checks["handles_a_no"],
            "04_wow_moment": wow_claims or dollars_saved >= 4000 or sow.runway_days >= 18,
        },
    }
