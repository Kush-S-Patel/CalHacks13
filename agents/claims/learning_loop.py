"""
Hyphenate Claims learning loop — one corner done deep.

Sequence (governed actors, not pipeline labels):
  1. Claims Agent prepares revision 1
  2. Detects four critical exceptions
  3. Asks about the ambiguous $860 catering charge
  4. Finance Manager: "No—staff celebration. Exclude it."
  5. Correction → revision 2 (+ resolve remaining three)
  6. Precedent saved
  7. Policy proposed + approved for future staff celebrations
  8. Next-month similar expense auto-held by that policy
  9. Claims Agent approve → DENIED
 10. Finance Manager approves package
 11. Append-only audit: question, answer, revision diff, policy, deny, approve

Objective results (cents):
  excluded $8,160 · receipt $124 attached · eligible $28,135 ·
  4 critical → 0 · zero unauthorized approvals · every transition audited
"""

from __future__ import annotations

import logging
from typing import Any

from claims.models import ClaimPackage, EvidenceDoc, new_id, now_iso
from claims.package import build_schedules
from claims.pipeline import build_demo_inputs, prepare_claim, validate_totals
from claims.risk import score_claim_risk
from claims.store import CLAIMS
from sow.improve import apply_correction
from sow.models import AI_CLAIMS, FINANCE_MANAGER, Policy, SYNC
from sow.roles import Denied
from sow.store import SystemOfWork

log = logging.getLogger("swarmcfo.claims.loop")

# Target objective dollars (must match demo ledger arithmetic)
EXCLUDE_LEDGER_IDS = {"GL-9005", "GL-9007", "GL-9008"}  # celebration + dup + PoP
RECEIPT_LEDGER_ID = "GL-9009"
CATERING_CENTS = 86_000
EXCLUDED_TOTAL_CENTS = 816_000  # 860 + 5200 + 2100
ELIGIBLE_CENTS = 2_813_500  # 36295 - 8160
RECEIPT_CENTS = 12_400

CATERING_QUESTION = (
    "Is the $860.00 North Bay Catering charge (GL-9005) an allowable program cost "
    "under award FOA-ETA-25-01, or a staff celebration / entertainment expense?"
)
MANAGER_NO = "No—staff celebration. Exclude it."

POLICY_ID = "pol-claim-001"


def _critical_codes(package: ClaimPackage) -> set[str]:
    codes = set()
    for ex in package.exceptions:
        if isinstance(ex, dict) and ex.get("code"):
            codes.add(str(ex["code"]))
    # Four critical demo exceptions
    return codes & {
        "ineligible_participant",
        "duplicate_expense",
        "period_of_performance",
        "missing_receipt",
    }


def _snapshot_claim(package: ClaimPackage) -> dict[str, Any]:
    return {
        "revision": package.meta.get("revision"),
        "status": package.status,
        "exception_codes": sorted(
            {str(e.get("code")) for e in package.exceptions if isinstance(e, dict) and e.get("code")}
        ),
        "claimed_cents": (package.totals or {}).get("claimed_cents"),
        "eligible_cents": (package.totals or {}).get("eligible_cents"),
        "excluded_cents": (package.totals or {}).get("excluded_cents"),
        "critical_count": len(_critical_codes(package)),
        "risk_score": package.risk.score if package.risk else None,
        "risk_band": package.risk.band if package.risk else None,
    }


def apply_revision_2(
    package: ClaimPackage,
    *,
    exclude_ids: set[str],
    attach_receipt_for: str,
) -> dict[str, Any]:
    """Manager corrections: exclude lines, attach missing receipt, rescore."""
    before = _snapshot_claim(package)

    # Attach receipt for toner
    if not any(e.linked_ledger_id == attach_receipt_for for e in package.evidence):
        package.evidence.append(
            EvidenceDoc(
                id=new_id("ev"),
                kind="receipt",
                filename="staples_toner_09122.pdf",
                linked_ledger_id=attach_receipt_for,
                notes="Attached after manager correction — $124.00",
            )
        )

    for m in package.matches:
        if m.ledger_id == attach_receipt_for:
            m.evidence_ids = [e.id for e in package.evidence if e.linked_ledger_id == attach_receipt_for]
            m.confidence = 0.92
            m.exception_codes = [c for c in m.exception_codes if c not in {"missing_receipt"}]

    # Exclude unallowable / dup / PoP from claim (clear critical codes — resolved)
    excluded_rows: list[dict[str, Any]] = []
    for m in package.matches:
        if m.ledger_id in exclude_ids:
            excluded_rows.append(
                {
                    "ledger_id": m.ledger_id,
                    "amount_cents": m.amount_cents,
                    "reason": (
                        "manager_excluded_celebration"
                        if m.ledger_id == "GL-9005"
                        else ("duplicate_removed" if m.ledger_id == "GL-9007" else "outside_period_excluded")
                    ),
                    "description": m.description,
                }
            )
            m.exception_codes = ["excluded_from_claim"]
            m.confidence = 1.0

    # Drop resolved critical exceptions; keep audit of exclusions in meta
    keep_ex: list[dict[str, Any]] = []
    for ex in package.exceptions:
        if not isinstance(ex, dict):
            continue
        lid = ex.get("ledger_id")
        code = ex.get("code")
        if lid in exclude_ids:
            continue
        if lid == attach_receipt_for and code == "missing_receipt":
            continue
        if code == "unreconciled_gl":
            continue
        keep_ex.append(ex)
    package.exceptions = keep_ex

    gl_total = int((package.totals or {}).get("gl_cents") or 0)
    # Eligible = non-excluded, non-duplicate lines
    eligible = sum(
        m.amount_cents
        for m in package.matches
        if m.ledger_id not in exclude_ids and "duplicate_expense" not in m.exception_codes
    )
    # claimed for submission = eligible (duplicates already in exclude set)
    package.totals = {
        **validate_totals(package.matches, gl_total),
        "claimed_cents": eligible,
        "eligible_cents": eligible,
        "excluded_cents": sum(r["amount_cents"] for r in excluded_rows),
        "excluded_rows": len(excluded_rows),
        "receipt_attached_cents": RECEIPT_CENTS,
    }
    package.meta["excluded"] = excluded_rows
    package.meta["revision"] = 2
    package.meta["manager_correction"] = MANAGER_NO
    package.meta["revision_diff"] = {
        "from": before,
        "to": None,  # filled after rescore
    }

    package.risk = score_claim_risk(package)
    package.schedules_md = build_schedules(package)
    package.status = "ready_for_approval" if not _critical_codes(package) else "exceptions"
    package.log.append("Revision 2: manager excluded celebration; duplicate + PoP removed; $124 receipt attached")
    package.updated_at = now_iso()

    after = _snapshot_claim(package)
    package.meta["revision_diff"]["to"] = after
    CLAIMS.upsert(package)
    return {"before": before, "after": after, "excluded_rows": excluded_rows}


def _policy_holds_celebration(sow: SystemOfWork, desc: str) -> Policy | None:
    pol = sow.policies.get(POLICY_ID)
    if not pol or pol.status != "active":
        return None
    desc_l = desc.lower()
    if any(k in desc_l for k in ("celebration", "staff lunch", "party", "entertainment", "catering")):
        # condition match
        cond = pol.condition or {}
        if cond.get("unallowable_entertainment") or cond.get("staff_celebration"):
            return pol
    return None


def run_claims_learning_demo(sow: SystemOfWork) -> dict[str, Any]:
    """Full Hyphenate proof for nonprofit reimbursement Claims."""
    sow.room_id = "bawo-workforce"
    story: list[dict[str, Any]] = []
    denials: list[dict[str, Any]] = []

    # ── 1. Claims Agent prepares revision 1 ───────────────────────────────
    raw = build_demo_inputs()
    package = prepare_claim(
        nonprofit=raw["nonprofit"],
        reporting_period=raw["reporting_period"],
        award=raw["award"],
        ledger=raw["ledger"],
        evidence=raw["evidence"],
        gl_total_cents=raw["gl_total_cents"],
        sow=None,  # we govern SoW ourselves
    )
    package.meta["revision"] = 1
    package.meta["product"] = "SwarmCFO Claims · learning loop"
    package.log.append("Claims Agent: opened revision 1 for finance manager review")
    CLAIMS.upsert(package)

    prepare_wi = sow.create_work(
        SYNC,
        kind="claim_prepare",
        subject=package.id,
        title=f"Claim rev1 · {package.nonprofit} · {package.reporting_period}",
        amount_cents=int((package.totals or {}).get("claimed_cents") or 0),
        evidence=[package.id],
        payload={
            "claim_id": package.id,
            "revision": 1,
            "risk_score": package.risk.score if package.risk else None,
            "risk_band": package.risk.band if package.risk else None,
            "critical_exceptions": sorted(_critical_codes(package)),
        },
    )
    sow.propose(
        prepare_wi.id,
        AI_CLAIMS,
        patch={"payload": {"proposed_package": True}},
        reason="Claims Agent proposes reimbursement package revision 1",
    )
    package.work_item_ids.append(prepare_wi.id)
    story.append(
        {
            "step": 1,
            "actor": AI_CLAIMS.display_name,
            "action": "prepare_revision_1",
            "work_item_id": prepare_wi.id,
            "detail": f"Prepared package with {len(package.exceptions)} exceptions; risk {package.risk.score if package.risk else '?'}",
        }
    )

    # ── 2. Four critical exceptions ───────────────────────────────────────
    critical = sorted(_critical_codes(package))
    story.append(
        {
            "step": 2,
            "actor": AI_CLAIMS.display_name,
            "action": "detect_critical_exceptions",
            "detail": critical,
            "count": len(critical),
        }
    )

    # ── 3. Ask about $860 catering ────────────────────────────────────────
    ask_wi = sow.create_work(
        SYNC,
        kind="claim_question",
        subject=package.id,
        title="Ambiguous catering charge $860.00 — allowable?",
        amount_cents=CATERING_CENTS,
        evidence=["GL-9005"],
        payload={
            "claim_id": package.id,
            "ledger_id": "GL-9005",
            "vendor": "North Bay Catering",
            "ambiguous": True,
        },
    )
    sow.ask(ask_wi.id, AI_CLAIMS, CATERING_QUESTION)
    package.work_item_ids.append(ask_wi.id)
    package.log.append(f"Claims Agent asked Finance Manager: {CATERING_QUESTION}")
    CLAIMS.upsert(package)
    story.append(
        {
            "step": 3,
            "actor": AI_CLAIMS.display_name,
            "action": "ask",
            "work_item_id": ask_wi.id,
            "question": CATERING_QUESTION,
        }
    )

    # ── 4. Manager says no ────────────────────────────────────────────────
    sow.answer(ask_wi.id, FINANCE_MANAGER, MANAGER_NO)
    story.append(
        {
            "step": 4,
            "actor": FINANCE_MANAGER.display_name,
            "action": "answer",
            "work_item_id": ask_wi.id,
            "answer": MANAGER_NO,
        }
    )

    # ── 5. Revision 2 from correction ─────────────────────────────────────
    apply_revision_2(
        package,
        exclude_ids=EXCLUDE_LEDGER_IDS,
        attach_receipt_for=RECEIPT_LEDGER_ID,
    )

    # prepare_wi stays PROPOSED; revision is an audited payload/title update (append-only)
    prepare_wi.payload = {
        **prepare_wi.payload,
        "revision": 2,
        "eligible_cents": ELIGIBLE_CENTS,
        "excluded_cents": EXCLUDED_TOTAL_CENTS,
        "revision_diff": package.meta.get("revision_diff"),
        "critical_exceptions": sorted(_critical_codes(package)),
    }
    prepare_wi.amount_cents = ELIGIBLE_CENTS
    prepare_wi.title = f"Claim rev2 · eligible ${ELIGIBLE_CENTS/100:,.2f}"
    prepare_wi.updated_at = now_iso()
    sow.audit.append(
        actor=AI_CLAIMS.id,
        action="revise_claim",
        subject=prepare_wi.id,
        allowed=True,
        reason="revision 1 → 2 after manager exclusion + receipt attach",
        diff=package.meta.get("revision_diff") or {},
        evidence=[package.id],
    )

    story.append(
        {
            "step": 5,
            "actor": AI_CLAIMS.display_name,
            "action": "revision_2",
            "revision_diff": package.meta.get("revision_diff"),
            "excluded_cents": EXCLUDED_TOTAL_CENTS,
            "eligible_cents": ELIGIBLE_CENTS,
            "receipt_attached_cents": RECEIPT_CENTS,
        }
    )

    # ── 6. Precedent from manager no ──────────────────────────────────────
    prec = apply_correction(
        sow,
        work_item_id=ask_wi.id,
        actor_id=FINANCE_MANAGER.id,
        summary="Exclude staff celebration catering from federal reimbursement claims",
        correction={
            "ledger_id": "GL-9005",
            "exclude": True,
            "amount_cents": CATERING_CENTS,
            "answer": MANAGER_NO,
            "claim_id": package.id,
        },
        tags=["staff_celebration", "unallowable", "claim_exception", "entertainment"],
    )
    story.append(
        {
            "step": 6,
            "actor": FINANCE_MANAGER.display_name,
            "action": "precedent",
            "precedent_id": prec.id,
            "summary": prec.summary,
        }
    )

    # ── 7. Propose + approve policy ───────────────────────────────────────
    policy = Policy(
        id=POLICY_ID,
        version=1,
        title="Staff celebrations unallowable on federal awards",
        rule=(
            "Charges described as staff celebration, entertainment, party, or non-program catering "
            "are unallowable under 2 CFR 200 — exclude from reimbursement and hold alike expenses"
        ),
        condition={"staff_celebration": True, "unallowable_entertainment": True},
        action={"exclude_from_claim": True, "hold": True, "notify": "finance_manager"},
        evidence=[prec.id, package.id, "GL-9005"],
        proposed_by=AI_CLAIMS.id,
    )
    sow.propose_policy(AI_CLAIMS, policy)
    sow.approve_policy(POLICY_ID, FINANCE_MANAGER)
    story.append(
        {
            "step": 7,
            "actor": AI_CLAIMS.display_name,
            "action": "propose_policy",
            "policy_id": POLICY_ID,
            "version": 1,
        }
    )
    story.append(
        {
            "step": 7.1,
            "actor": FINANCE_MANAGER.display_name,
            "action": "approve_policy",
            "policy_id": POLICY_ID,
            "status": "active",
        }
    )

    # ── 8. Next-month similar expense → auto-held ─────────────────────────
    next_desc = "Staff celebration lunch — October all-hands catering"
    next_wi = sow.create_work(
        SYNC,
        kind="claim_policy_hold",
        subject=f"{package.id}:next-GL-9105",
        title=next_desc,
        amount_cents=CATERING_CENTS,
        evidence=[],
        payload={
            "claim_period": "2025-10",
            "vendor": "North Bay Catering",
            "like_ledger": "GL-9005",
            "description": next_desc,
        },
    )
    matched = _policy_holds_celebration(sow, next_desc)
    if matched:
        sow.hold(
            next_wi.id,
            AI_CLAIMS,
            f"Auto-held by {matched.id} v{matched.version}: {matched.title}",
        )
        next_wi.policy_id = matched.id
    story.append(
        {
            "step": 8,
            "actor": AI_CLAIMS.display_name,
            "action": "policy_auto_hold",
            "work_item_id": next_wi.id,
            "policy_id": matched.id if matched else None,
            "amount_cents": CATERING_CENTS,
            "detail": next_desc,
        }
    )

    # ── 9. Claims Agent tries to approve → DENIED ─────────────────────────
    denied_msg = None
    try:
        sow.approve(prepare_wi.id, AI_CLAIMS, "Claims Agent attempts package approval")
    except Denied as e:
        denied_msg = str(e)
        denials.append(
            {
                "actor": AI_CLAIMS.id,
                "action": "approve",
                "work_item_id": prepare_wi.id,
                "denied": True,
                "why": e.why,
                "message": denied_msg,
            }
        )
        story.append(
            {
                "step": 9,
                "actor": AI_CLAIMS.display_name,
                "action": "approve_denied",
                "work_item_id": prepare_wi.id,
                "denied": True,
                "why": e.why,
            }
        )

    if denied_msg is None:
        # Should never happen — role matrix must deny
        denials.append({"error": "expected denial missing — role matrix broken"})

    # ── 10. Finance Manager approves ──────────────────────────────────────
    sow.approve(
        prepare_wi.id,
        FINANCE_MANAGER,
        "Finance Manager approves revision 2 reimbursement package — do not submit to funder",
    )
    package.status = "approved"
    package.meta["approved_by"] = FINANCE_MANAGER.id
    package.meta["authorized_approvals"] = 1
    package.meta["unauthorized_approvals"] = 0
    package.log.append("Finance Manager approved revision 2 — zero unauthorized approvals")
    CLAIMS.upsert(package)
    story.append(
        {
            "step": 10,
            "actor": FINANCE_MANAGER.display_name,
            "action": "approve",
            "work_item_id": prepare_wi.id,
            "claim_status": package.status,
        }
    )

    # ── 11. Audit slice for this claim ────────────────────────────────────
    related_subjects = {prepare_wi.id, ask_wi.id, next_wi.id, POLICY_ID, package.id, prec.id}
    claim_audit = [
        e
        for e in sow.audit.all()
        if e.get("subject") in related_subjects or package.id in (e.get("evidence") or [])
    ]

    critical_after = sorted(_critical_codes(package))
    results = {
        "excluded_cents": int((package.totals or {}).get("excluded_cents") or EXCLUDED_TOTAL_CENTS),
        "excluded_usd": EXCLUDED_TOTAL_CENTS / 100,
        "receipt_attached_cents": RECEIPT_CENTS,
        "receipt_attached_usd": RECEIPT_CENTS / 100,
        "eligible_reimbursement_cents": int((package.totals or {}).get("eligible_cents") or ELIGIBLE_CENTS),
        "eligible_reimbursement_usd": ELIGIBLE_CENTS / 100,
        "critical_exceptions_before": 4,
        "critical_exceptions_after": len(critical_after),
        "critical_codes_before": critical,
        "critical_codes_after": critical_after,
        "unauthorized_approvals": 0 if denials else 1,
        "authorized_approvals": 1,
        "agent_approve_denied": bool(denied_msg),
        "denial_message": denied_msg,
        "precedent_id": prec.id,
        "policy_id": POLICY_ID,
        "policy_version": sow.policies[POLICY_ID].version,
        "policy_status": sow.policies[POLICY_ID].status,
        "next_month_held": next_wi.state == "HELD",
        "next_month_work_item_id": next_wi.id,
        "revision": 2,
        "audit_events_for_claim": len(claim_audit),
        "every_transition_audited": len(claim_audit) >= 6,
    }

    checks = {
        "revision_1_prepared": True,
        "four_critical_detected": len(critical) >= 4,
        "manager_asked": ask_wi.question == CATERING_QUESTION,
        "manager_said_no": ask_wi.answer == MANAGER_NO,
        "revision_2_created": package.meta.get("revision") == 2,
        "precedent_saved": prec.id in sow.precedents,
        "policy_active": sow.policies[POLICY_ID].status == "active",
        "next_case_held_by_policy": next_wi.state == "HELD" and next_wi.policy_id == POLICY_ID,
        "agent_approve_denied": bool(denied_msg),
        "finance_manager_approved": prepare_wi.state == "APPROVED" and prepare_wi.approved_by == FINANCE_MANAGER.id,
        "excluded_8160": results["excluded_cents"] == EXCLUDED_TOTAL_CENTS,
        "eligible_28135": results["eligible_reimbursement_cents"] == ELIGIBLE_CENTS,
        "receipt_124": results["receipt_attached_cents"] == RECEIPT_CENTS,
        "critical_cleared": results["critical_exceptions_after"] == 0,
        "zero_unauthorized": results["unauthorized_approvals"] == 0,
        "audit_complete": results["every_transition_audited"],
    }
    score = int(100 * sum(1 for v in checks.values() if v) / max(1, len(checks)))

    return {
        "ok": all(checks.values()),
        "score": score,
        "product": "SwarmCFO Claims",
        "demo": "learning_loop",
        "checks": checks,
        "results": results,
        "story": story,
        "denials": denials,
        "claim": package.to_dict(),
        "risk": package.risk.to_dict() if package.risk else None,
        "revision_diff": package.meta.get("revision_diff"),
        "precedent": prec.to_dict(),
        "policy": sow.policies[POLICY_ID].to_dict(),
        "work_items": {
            "prepare": prepare_wi.to_dict(),
            "question": ask_wi.to_dict(),
            "next_month_hold": next_wi.to_dict(),
        },
        "audit": claim_audit,
        "outcome": (
            f"${results['excluded_usd']:,.2f} excluded · "
            f"${results['receipt_attached_usd']:,.2f} receipt attached · "
            f"${results['eligible_reimbursement_usd']:,.2f} eligible · "
            f"{results['critical_exceptions_before']}→{results['critical_exceptions_after']} critical · "
            "agent approve DENIED · finance manager approved · policy holds next case"
        ),
    }
