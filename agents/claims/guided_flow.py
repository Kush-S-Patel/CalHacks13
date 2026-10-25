"""Explicit, stepwise claim-review actions used by the judged demo.

The legacy learning-loop endpoint intentionally remains available.  This module
provides the honest version of that story: a manager decision changes only the
line being decided, every other exception needs its own explicit resolution,
policy proposal and activation are separate actions, and claim approval keeps
the AI/human separation-of-duties boundary visible.
"""

from __future__ import annotations

from typing import Any, Literal

from claims.guided_persistence import GUIDED_PERSISTENCE
from claims.learning_loop import CATERING_CENTS, CATERING_QUESTION
from claims.models import AwardRulebook, ClaimPackage, EvidenceDoc, now_iso
from claims.package import build_schedules
from claims.pipeline import prepare_claim, validate_totals
from claims.risk import score_claim_risk
from claims.session import get_pending, pop_pending, recover_pending
from claims.store import CLAIMS
from sow.improve import apply_correction
from sow.models import AI_CLAIMS, FINANCE_MANAGER, SYNC, Policy
from sow.roles import Denied
from sow.store import SystemOfWork

CATERING_LEDGER_ID = "GL-9005"


def _required_reason(reason: str) -> str:
    clean = (reason or "").strip()
    if not clean:
        raise ValueError("reason is required")
    return clean


def _package(claim_id: str) -> ClaimPackage:
    package = CLAIMS.get(claim_id)
    if not package:
        raise KeyError(f"unknown claim {claim_id}")
    return package


def _restore(sow: SystemOfWork, package: ClaimPackage) -> None:
    GUIDED_PERSISTENCE.restore_claim(sow, package.id)


def _flow(package: ClaimPackage) -> dict[str, Any]:
    flow = package.meta.setdefault(
        "guided_flow",
        {
            "phase": "awaiting_decision",
            "decision": None,
            "resolved_exceptions": [],
            "policy_id": None,
            "policy_status": None,
            "ai_approval_receipt": None,
            "manager_approval": None,
        },
    )
    return flow


def _match(package: ClaimPackage, ledger_id: str):
    match = next((m for m in package.matches if m.ledger_id == ledger_id), None)
    if not match:
        raise KeyError(f"unknown ledger line {ledger_id} on claim {package.id}")
    return match


def _blocking_exceptions(package: ClaimPackage) -> list[dict[str, Any]]:
    """Fail closed: every unresolved package exception blocks approval."""
    return [
        dict(ex)
        for ex in package.exceptions
        if isinstance(ex, dict) and str(ex.get("code") or "")
    ]


def _sync_unreconciled_exception(package: ClaimPackage) -> None:
    """Keep the package-level duplicate reconciliation warning honest."""
    has_unresolved_duplicate = any("duplicate_expense" in m.exception_codes for m in package.matches)
    package.exceptions = [
        ex
        for ex in package.exceptions
        if not (isinstance(ex, dict) and ex.get("code") == "unreconciled_gl")
    ]
    if has_unresolved_duplicate:
        duplicate_cents = sum(
            m.amount_cents for m in package.matches if "duplicate_expense" in m.exception_codes
        )
        package.exceptions.append(
            {
                "code": "unreconciled_gl",
                "message": "Claimed total excludes duplicate lines; reconcile before submission",
                "gap_cents": duplicate_cents,
                "evidence_backed": True,
            }
        )


def _recalculate(package: ClaimPackage) -> None:
    gl_total = int((package.totals or {}).get("gl_cents") or 0)
    package.totals = validate_totals(package.matches, gl_total)
    package.totals["eligible_cents"] = package.totals["claimed_cents"]
    package.totals["excluded_rows"] = sum(
        1 for m in package.matches if "excluded_from_claim" in m.exception_codes
    )
    attached = int(_flow(package).get("receipt_attached_cents") or 0)
    if attached:
        package.totals["receipt_attached_cents"] = attached
    package.risk = score_claim_risk(package)
    package.status = "exceptions" if _blocking_exceptions(package) else "ready_for_approval"
    package.updated_at = now_iso()
    package.schedules_md = build_schedules(package)
    CLAIMS.upsert(package)


def _claim_snapshot(package: ClaimPackage) -> dict[str, Any]:
    totals = package.totals or {}
    return {
        "revision": int(package.meta.get("revision") or 1),
        "status": package.status,
        "eligible_cents": int(totals.get("eligible_cents") or totals.get("claimed_cents") or 0),
        "excluded_cents": int(totals.get("excluded_cents") or 0),
        "duplicate_cents": int(totals.get("duplicate_cents") or 0),
        "recon_gap_cents": int(totals.get("recon_gap_cents") or 0),
        "critical_exceptions": sorted(
            {
                str(ex.get("code"))
                for ex in package.exceptions
                if isinstance(ex, dict) and ex.get("code")
            }
        ),
    }


def _sync_prepare_work_item(
    sow: SystemOfWork,
    package: ClaimPackage,
    *,
    reason: str,
) -> None:
    """Keep the approvable work item identical to the current claim revision."""
    prepare = _prepare_work_item(sow, package)
    before = {
        "revision": prepare.payload.get("revision"),
        "amount_cents": prepare.amount_cents,
        "critical_exceptions": prepare.payload.get("critical_exceptions"),
    }
    current = _claim_snapshot(package)
    prepare.amount_cents = current["eligible_cents"]
    prepare.title = (
        f"September claim rev{current['revision']} · "
        f"${current['eligible_cents']/100:,.2f} eligible"
    )
    prepare.payload = {
        **prepare.payload,
        **current,
        "claim_id": package.id,
        "revision_diff": package.meta.get("revision_diff"),
        "proposed_package": True,
    }
    prepare.updated_at = now_iso()
    after = {
        "revision": prepare.payload.get("revision"),
        "amount_cents": prepare.amount_cents,
        "critical_exceptions": prepare.payload.get("critical_exceptions"),
    }
    sow.audit.append(
        actor=AI_CLAIMS.id,
        action="revise_claim",
        subject=prepare.id,
        allowed=True,
        reason=reason,
        diff={"from": before, "to": after},
        evidence=[package.id, prepare.id],
    )


def _prepare_work_item(sow: SystemOfWork, package: ClaimPackage):
    flow = _flow(package)
    item_id = flow.get("prepare_work_item_id")
    if not item_id:
        item_id = next(
            (
                wid
                for wid in package.work_item_ids
                if wid in sow.work_items and sow.work_items[wid].kind == "claim_prepare"
            ),
            None,
        )
    if not item_id or item_id not in sow.work_items:
        raise RuntimeError("claim preparation work item is unavailable; start the review again")
    return sow.work_items[item_id]


def _future_policy_match(
    policy: Policy,
    *,
    vendor: str,
    description: str,
) -> dict[str, Any] | None:
    """Return an explainable match only for the exact approved learned policy.

    The ordinary claim pipeline intentionally does not flag the demo description.
    This matcher is the separate, policy-backed step that recognizes a staff-event
    pattern after Priya has approved it.
    """
    if policy.status != "active" or policy.approved_by != FINANCE_MANAGER.id:
        return None
    if not bool((policy.action or {}).get("hold")):
        return None

    condition = policy.condition or {}
    condition_signals = [
        key
        for key in (
            "staff_celebration",
            "unallowable_entertainment",
            "documented_program_purpose",
        )
        if bool(condition.get(key))
    ]
    if not condition_signals:
        return None

    searchable = f"{vendor} {description}".lower()
    learned_terms = (
        "staff lunch",
        "staff event",
        "all-hands",
        "all hands",
        "team lunch",
        "catering",
    )
    matched_terms = [term for term in learned_terms if term in searchable]
    if not matched_terms:
        return None
    return {
        "matcher": "approved_policy_condition_v1",
        "policy_id": policy.id,
        "policy_version": policy.version,
        "approved_by": policy.approved_by,
        "condition_signals": condition_signals,
        "matched_terms": matched_terms,
        "vendor": vendor,
        "description": description,
    }


def _future_submission_result(
    sow: SystemOfWork,
    *,
    source: ClaimPackage,
    target: ClaimPackage,
    idempotent: bool,
) -> dict[str, Any]:
    flow = _flow(source)
    policy_id = str(flow.get("future_claim_policy_id") or flow.get("policy_id") or "")
    work_item_id = str(flow.get("future_claim_work_item_id") or "")
    policy = sow.policies.get(policy_id)
    work_item = sow.work_items.get(work_item_id)
    if not policy or not work_item:
        raise RuntimeError("future-claim proof artifacts are unavailable")
    return {
        "ok": True,
        "idempotent": idempotent,
        "phase": flow.get("phase"),
        "policy": policy.to_dict(),
        "future_claim_work_item": work_item.to_dict(),
        "match_basis": flow.get("future_claim_match_basis"),
        "baseline": (target.meta or {}).get("baseline_before_learned_policy"),
        "claim": source.to_dict(),
        "future_claim": target.to_dict(),
    }


def submit_decision(
    sow: SystemOfWork,
    *,
    claim_id: str,
    decision: Literal["exclude", "keep"],
    reason: str,
) -> dict[str, Any]:
    """Record Priya's catering decision without touching unrelated lines."""
    clean_reason = _required_reason(reason)
    package = _package(claim_id)
    _restore(sow, package)
    flow = _flow(package)
    if flow.get("decision"):
        raise RuntimeError("a manager decision is already recorded for this claim")

    pending = get_pending(claim_id) or recover_pending(sow, claim_id)
    if not pending:
        raise RuntimeError("claim is not awaiting a manager decision; start the review first")
    ask_id = str(pending["ask_wi_id"])
    prepare_id = str(pending["prepare_wi_id"])
    ask = sow.work_items.get(ask_id)
    if not ask or ask.state != "NEEDS_INFO":
        raise RuntimeError("catering question is not awaiting an answer")

    before_snapshot = _claim_snapshot(package)
    answer = f"{decision.upper()}: {clean_reason}"
    sow.answer(ask.id, FINANCE_MANAGER, answer)
    catering = _match(package, CATERING_LEDGER_ID)

    if decision == "exclude":
        # The exclusion resolves every issue attached to this one line only.
        package.exceptions = [
            ex
            for ex in package.exceptions
            if not (isinstance(ex, dict) and ex.get("ledger_id") == CATERING_LEDGER_ID)
        ]
        catering.exception_codes = ["excluded_from_claim"]
        catering.confidence = 1.0
    else:
        # Priya supplies the program-purpose fact, but missing evidence remains.
        package.exceptions = [
            ex
            for ex in package.exceptions
            if not (
                isinstance(ex, dict)
                and ex.get("ledger_id") == CATERING_LEDGER_ID
                and ex.get("code") == "ineligible_participant"
            )
        ]
        catering.exception_codes = [
            code for code in catering.exception_codes if code != "ineligible_participant"
        ]

    decision_record = {
        "ledger_id": CATERING_LEDGER_ID,
        "decision": decision,
        "reason": clean_reason,
        "actor": FINANCE_MANAGER.id,
        "amount_cents": CATERING_CENTS,
        "at": now_iso(),
    }
    flow.update(
        {
            "phase": "decision_recorded",
            "prepare_work_item_id": prepare_id,
            "question_work_item_id": ask_id,
            "decision": decision_record,
        }
    )
    package.meta["revision"] = 2
    package.meta["awaiting_manager"] = False
    package.log.append(f"Priya {decision}d GL-9005: {clean_reason}")
    _sync_unreconciled_exception(package)
    _recalculate(package)
    package.meta["revision_diff"] = {
        "from": before_snapshot,
        "to": _claim_snapshot(package),
    }
    event = sow.audit.append(
        actor=FINANCE_MANAGER.id,
        action="claim_line_decision",
        subject=package.id,
        allowed=True,
        reason=clean_reason,
        diff={
            "GL-9005": {
                "decision": decision,
                "amount_cents": CATERING_CENTS,
            }
        },
        evidence=[package.id, CATERING_LEDGER_ID],
    )
    _sync_prepare_work_item(sow, package, reason="Rebuilt claim after the manager decision")
    CLAIMS.upsert(package)
    pop_pending(claim_id)
    GUIDED_PERSISTENCE.save_claim(sow, package)
    return {
        "ok": True,
        "phase": flow["phase"],
        "decision": decision_record,
        "audit_receipt": event.to_dict(),
        "unresolved_exceptions": _blocking_exceptions(package),
        "claim": package.to_dict(),
    }


def resolve_exception(
    sow: SystemOfWork,
    *,
    claim_id: str,
    ledger_id: str,
    action: Literal["exclude", "attach_receipt"],
    reason: str,
    evidence_id: str | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """Resolve one named line explicitly; never batch-fix other exceptions."""
    clean_reason = _required_reason(reason)
    package = _package(claim_id)
    _restore(sow, package)
    flow = _flow(package)
    if not flow.get("decision"):
        raise RuntimeError("record the catering decision before resolving other exceptions")
    if flow.get("phase") != "decision_recorded":
        raise RuntimeError(f"exceptions cannot be resolved during phase {flow.get('phase')}")
    match = _match(package, ledger_id)
    before = list(match.exception_codes)
    if not before or before == ["excluded_from_claim"]:
        raise RuntimeError(f"ledger line {ledger_id} has no unresolved exception")

    receipt_cents = 0
    if action == "exclude":
        package.exceptions = [
            ex
            for ex in package.exceptions
            if not (isinstance(ex, dict) and ex.get("ledger_id") == ledger_id)
        ]
        match.exception_codes = ["excluded_from_claim"]
        match.confidence = 1.0
    else:
        if not evidence_id or not evidence_id.strip() or not filename or not filename.strip():
            raise ValueError("evidence_id and filename are required when attaching a receipt")
        if not ({"missing_receipt", "missing_payroll"} & set(match.exception_codes)):
            raise RuntimeError(f"ledger line {ledger_id} is not missing supporting evidence")
        clean_evidence_id = evidence_id.strip()
        if any(e.id == clean_evidence_id for e in package.evidence):
            raise ValueError(f"evidence id {clean_evidence_id} already exists")
        package.evidence.append(
            EvidenceDoc(
                id=clean_evidence_id,
                kind="receipt",
                filename=filename.strip(),
                linked_ledger_id=ledger_id,
                notes=clean_reason,
            )
        )
        match.evidence_ids.append(clean_evidence_id)
        match.exception_codes = [
            code for code in match.exception_codes if code not in {"missing_receipt", "missing_payroll"}
        ]
        match.confidence = max(match.confidence, 0.92)
        package.exceptions = [
            ex
            for ex in package.exceptions
            if not (
                isinstance(ex, dict)
                and ex.get("ledger_id") == ledger_id
                and ex.get("code") in {"missing_receipt", "missing_payroll"}
            )
        ]
        receipt_cents = match.amount_cents
        flow["receipt_attached_cents"] = int(flow.get("receipt_attached_cents") or 0) + receipt_cents

    resolution = {
        "ledger_id": ledger_id,
        "action": action,
        "reason": clean_reason,
        "actor": FINANCE_MANAGER.id,
        "before": before,
        "after": list(match.exception_codes),
        "evidence_id": evidence_id.strip() if evidence_id else None,
        "at": now_iso(),
    }
    flow.setdefault("resolved_exceptions", []).append(resolution)
    package.log.append(f"Priya resolved {ledger_id} via {action}: {clean_reason}")
    _sync_unreconciled_exception(package)
    _recalculate(package)
    revision_diff = package.meta.setdefault("revision_diff", {"from": None, "to": None})
    revision_diff["to"] = _claim_snapshot(package)
    if package.status == "ready_for_approval":
        flow["phase"] = "ready_for_policy"
    event = sow.audit.append(
        actor=FINANCE_MANAGER.id,
        action="resolve_claim_exception",
        subject=package.id,
        allowed=True,
        reason=clean_reason,
        diff={ledger_id: {"from": before, "to": list(match.exception_codes)}},
        evidence=[package.id, ledger_id] + ([evidence_id.strip()] if evidence_id else []),
    )
    _sync_prepare_work_item(sow, package, reason=f"Rebuilt claim after resolving {ledger_id}")
    CLAIMS.upsert(package)
    GUIDED_PERSISTENCE.save_claim(sow, package)
    return {
        "ok": True,
        "phase": flow["phase"],
        "resolution": resolution,
        "audit_receipt": event.to_dict(),
        "unresolved_exceptions": _blocking_exceptions(package),
        "claim": package.to_dict(),
    }


def propose_policy(sow: SystemOfWork, *, claim_id: str, reason: str) -> dict[str, Any]:
    """Turn the recorded manager decision into a proposed rule, without activating it."""
    clean_reason = _required_reason(reason)
    package = _package(claim_id)
    _restore(sow, package)
    flow = _flow(package)
    if package.status != "ready_for_approval" or flow.get("phase") != "ready_for_policy":
        raise RuntimeError("resolve every claim exception before proposing a policy")
    decision = flow.get("decision") or {}
    decision_kind = str(decision.get("decision") or "")
    if decision_kind not in {"exclude", "keep"}:
        raise RuntimeError("a manager decision is required before proposing this policy")
    existing_id = flow.get("policy_id")
    if existing_id and existing_id in sow.policies:
        raise RuntimeError("a policy is already proposed for this claim")

    ask_id = str(flow.get("question_work_item_id") or "")
    if not ask_id or ask_id not in sow.work_items:
        raise RuntimeError("decision work item is unavailable")
    excluded = decision_kind == "exclude"
    precedent = apply_correction(
        sow,
        work_item_id=ask_id,
        actor_id=FINANCE_MANAGER.id,
        summary=(
            "Exclude staff-celebration catering from federal reimbursement claims"
            if excluded
            else "Require documented program purpose before claiming staff-event catering"
        ),
        correction={
            "claim_id": claim_id,
            "ledger_id": CATERING_LEDGER_ID,
            "decision": decision_kind,
            "reason": decision.get("reason"),
        },
        tags=[
            "staff_celebration",
            "claim_exception",
            "entertainment",
            "excluded" if excluded else "documented_program_purpose",
        ],
    )
    policy_id = f"pol-claim-{claim_id.rsplit('-', 1)[-1]}"
    policy = Policy(
        id=policy_id,
        version=1,
        title=(
            "Staff celebrations stay off federal awards"
            if excluded
            else "Staff-event costs require documented program purpose"
        ),
        rule=(
            (
                "If a charge is for a staff celebration or non-program entertainment, exclude it "
                "from the reimbursement package and hold a similar charge for human review."
            )
            if excluded
            else (
                "If a staff-event cost may have a direct programmatic purpose, require supporting "
                "evidence and hold it for a finance manager decision before reimbursement."
            )
        ),
        condition={
            "staff_celebration": True,
            "unallowable_entertainment": excluded,
            "documented_program_purpose": not excluded,
        },
        action={
            "exclude_from_claim": excluded,
            "require_supporting_evidence": not excluded,
            "hold": True,
            "notify": "finance_manager",
        },
        evidence=[precedent.id, package.id, CATERING_LEDGER_ID],
    )
    sow.propose_policy(AI_CLAIMS, policy)
    flow.update(
        {
            "phase": "policy_pending_approval",
            "precedent_id": precedent.id,
            "policy_id": policy.id,
            "policy_status": policy.status,
            "policy_proposal_reason": clean_reason,
        }
    )
    package.log.append(f"Jordan proposed {policy.id}: {clean_reason}")
    event = sow.audit.append(
        actor=AI_CLAIMS.id,
        action="claim_policy_proposal_context",
        subject=package.id,
        allowed=True,
        reason=clean_reason,
        diff={"policy_status": {"from": None, "to": "needs_approval"}},
        evidence=[package.id, policy.id, precedent.id],
    )
    CLAIMS.upsert(package)
    GUIDED_PERSISTENCE.save_claim(sow, package)
    return {
        "ok": True,
        "phase": flow["phase"],
        "policy": policy.to_dict(),
        "precedent": precedent.to_dict(),
        "audit_receipt": event.to_dict(),
        "claim": package.to_dict(),
    }


def approve_policy(sow: SystemOfWork, *, policy_id: str, reason: str) -> dict[str, Any]:
    """Activate a proposed guided-flow policy as a distinct human action."""
    clean_reason = _required_reason(reason)
    package = next(
        (
            p
            for p in CLAIMS.packages.values()
            if (p.meta.get("guided_flow") or {}).get("policy_id") == policy_id
        ),
        None,
    )
    if not package:
        raise KeyError(f"unknown guided policy {policy_id}")
    _restore(sow, package)
    policy = sow.policies.get(policy_id)
    if not policy:
        raise KeyError(f"policy {policy_id} is unavailable in the current system of work")
    if policy.status != "needs_approval":
        raise RuntimeError(f"policy {policy_id} is {policy.status}, expected needs_approval")
    flow = _flow(package)
    if flow.get("phase") != "policy_pending_approval":
        raise RuntimeError(f"policy cannot be approved during phase {flow.get('phase')}")

    sow.approve_policy(policy_id, FINANCE_MANAGER)
    flow.update(
        {
            "phase": "policy_active",
            "policy_status": policy.status,
            "policy_approval": {
                "actor": FINANCE_MANAGER.id,
                "reason": clean_reason,
                "at": now_iso(),
            },
        }
    )
    package.log.append(f"Priya activated {policy.id}: {clean_reason}")
    event = sow.audit.append(
        actor=FINANCE_MANAGER.id,
        action="claim_policy_approval",
        subject=package.id,
        allowed=True,
        reason=clean_reason,
        diff={"policy_status": {"from": "needs_approval", "to": "active"}},
        evidence=[package.id, policy.id],
    )
    CLAIMS.upsert(package)
    GUIDED_PERSISTENCE.save_claim(sow, package)
    return {
        "ok": True,
        "phase": flow["phase"],
        "policy": policy.to_dict(),
        "audit_receipt": event.to_dict(),
        "claim": package.to_dict(),
    }


def submit_next_period_claim(
    sow: SystemOfWork,
    *,
    source_claim_id: str,
    reason: str,
    reporting_period: str = "2025-10",
    ledger_id: str = "GL-9105",
    date: str = "2025-10-08",
    vendor: str = "Marina Cafe",
    description: str = "All-hands staff lunch — October",
    amount_cents: int = CATERING_CENTS,
    budget_line: str = "supplies",
    evidence_id: str = "ev-october-staff-lunch",
    filename: str = "october_staff_lunch.pdf",
) -> dict[str, Any]:
    """Submit an independent October claim and apply only the learned policy.

    The target package is first run through the ordinary deterministic pipeline
    with valid evidence and no built-in exception.  Only then is the exact policy
    approved for the September source claim evaluated and its hold recorded.
    """
    clean_reason = _required_reason(reason)
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    if not reporting_period or not date.startswith(f"{reporting_period}-"):
        raise ValueError("date must fall within reporting_period")
    for field_name, value in {
        "ledger_id": ledger_id,
        "vendor": vendor,
        "description": description,
        "budget_line": budget_line,
        "evidence_id": evidence_id,
        "filename": filename,
    }.items():
        if not str(value or "").strip():
            raise ValueError(f"{field_name} is required")

    source = _package(source_claim_id)
    _restore(sow, source)
    flow = _flow(source)

    # Repeating the same stage action must not create another claim or hold.
    existing_target_id = flow.get("future_claim_id")
    if existing_target_id:
        target = CLAIMS.get(str(existing_target_id))
        if not target:
            raise RuntimeError("persisted future claim is unavailable")
        _restore(sow, target)
        GUIDED_PERSISTENCE.save_claim(sow, source)
        GUIDED_PERSISTENCE.save_claim(sow, target)
        return _future_submission_result(
            sow,
            source=source,
            target=target,
            idempotent=True,
        )

    if flow.get("phase") != "policy_active":
        raise RuntimeError(
            f"next-period claim cannot be submitted during phase {flow.get('phase')}"
        )
    policy_id = str(flow.get("policy_id") or "")
    policy = sow.policies.get(policy_id)
    if not policy:
        raise RuntimeError("the source claim's learned policy is unavailable")
    if policy.status != "active" or policy.approved_by != FINANCE_MANAGER.id:
        raise RuntimeError("the source claim's learned policy is not human-approved and active")

    match_basis = _future_policy_match(
        policy,
        vendor=vendor.strip(),
        description=description.strip(),
    )
    if not match_basis:
        raise RuntimeError("the approved learned policy does not match this submission")

    target = prepare_claim(
        nonprofit=source.nonprofit,
        reporting_period=reporting_period,
        award=AwardRulebook(**source.award.to_dict()),
        ledger=[
            {
                "id": ledger_id.strip(),
                "date": date,
                "vendor": vendor.strip(),
                "desc": description.strip(),
                "amount_cents": amount_cents,
                "budget_line": budget_line.strip(),
            }
        ],
        evidence=[
            EvidenceDoc(
                id=evidence_id.strip(),
                kind="receipt",
                filename=filename.strip(),
                linked_ledger_id=ledger_id.strip(),
                notes="Supporting record supplied with the independent October submission.",
            )
        ],
        gl_total_cents=amount_cents,
        sow=None,
    )
    baseline_codes = sorted(
        {
            code
            for item in target.matches
            for code in item.exception_codes
        }
        | {
            str(item.get("code"))
            for item in target.exceptions
            if isinstance(item, dict) and item.get("code")
        }
    )
    baseline = {
        "claim_id": target.id,
        "source_claim_id": source.id,
        "reporting_period": target.reporting_period,
        "status": target.status,
        "exception_codes": baseline_codes,
        "claimed_cents": int((target.totals or {}).get("claimed_cents") or 0),
        "evidence_ids": [item.id for item in target.evidence],
        "pipeline": "ordinary_claim_pipeline_before_learned_policy",
    }
    if baseline_codes or target.status != "ready_for_approval":
        raise RuntimeError(
            "independent submission was not clean before learned-policy evaluation"
        )

    target_match = _match(target, ledger_id.strip())
    target_match.exception_codes = ["learned_policy_hold"]
    target.exceptions = [
        {
            "code": "learned_policy_hold",
            "ledger_id": ledger_id.strip(),
            "message": "Held by the manager-approved policy learned from the September claim",
            "evidence_backed": True,
            "source_claim_id": source.id,
            "policy_id": policy.id,
            "policy_version": policy.version,
            "match_basis": match_basis,
        }
    ]
    excluded_cents = amount_cents if bool((policy.action or {}).get("exclude_from_claim")) else 0
    target.totals = {
        "claimed_cents": 0,
        "eligible_cents": 0,
        "gl_cents": amount_cents,
        "duplicate_cents": 0,
        "excluded_cents": excluded_cents,
        "held_cents": amount_cents,
        "recon_gap_cents": 0,
        "match_count": 1,
    }
    target.status = "exceptions"
    target.risk = score_claim_risk(target)
    target.meta.update(
        {
            "independent_submission": True,
            "source_claim_id": source.id,
            "baseline_before_learned_policy": baseline,
            "learned_policy_application": {
                "exception_code": "learned_policy_hold",
                "policy_id": policy.id,
                "policy_version": policy.version,
                "policy_status": policy.status,
                "approved_by": policy.approved_by,
                "source_claim_id": source.id,
                "match_basis": match_basis,
                "applied_at": now_iso(),
            },
        }
    )
    target.log.append(
        f"Independent submission held by approved policy {policy.id} v{policy.version}"
    )

    hold = sow.create_work(
        SYNC,
        kind="claim_policy_hold",
        subject=target.id,
        title=f"Policy hold · {reporting_period} · {vendor.strip()} ${amount_cents/100:,.2f}",
        amount_cents=amount_cents,
        evidence=[source.id, target.id, policy.id, ledger_id.strip(), evidence_id.strip()],
        payload={
            "claim_id": target.id,
            "source_claim_id": source.id,
            "claim_period": reporting_period,
            "ledger_id": ledger_id.strip(),
            "vendor": vendor.strip(),
            "description": description.strip(),
            "policy_id": policy.id,
            "policy_version": policy.version,
            "exception_code": "learned_policy_hold",
            "baseline_exception_codes": baseline_codes,
            "match_basis": match_basis,
        },
    )
    sow.propose(
        hold.id,
        AI_CLAIMS,
        patch={"policy_id": policy.id},
        reason=f"Apply approved policy {policy.id} v{policy.version} to independent claim {target.id}",
    )
    sow.hold(
        hold.id,
        AI_CLAIMS,
        f"{clean_reason} Policy {policy.id} v{policy.version} matched {', '.join(match_basis['matched_terms'])}.",
    )
    target.work_item_ids.append(hold.id)
    target.meta["learned_policy_application"]["work_item_id"] = hold.id
    target.schedules_md = "\n".join(
        [
            f"# Reimbursement package — {target.nonprofit}",
            "",
            f"**Reporting period:** {target.reporting_period}",
            f"**Independent claim:** `{target.id}`",
            f"**Source learned-policy claim:** `{source.id}`",
            "",
            "## Policy-held expenditure",
            f"- `{target_match.ledger_id}` {target_match.vendor} ${amount_cents/100:,.2f}",
            f"- Held by `{policy.id}` v{policy.version}; eligible pending human review: **$0.00**",
            f"- Exact exception: `learned_policy_hold`",
            "",
            "## Reconciliation",
            f"- GL total: **${amount_cents/100:,.2f}**",
            f"- Policy-held: **${amount_cents/100:,.2f}**",
            "- Recon gap: **$0.00**",
            "",
            "_Status: exceptions · not submitted · manager review required_",
        ]
    )

    target_event = sow.audit.append(
        actor=AI_CLAIMS.id,
        action="apply_learned_claim_policy",
        subject=target.id,
        allowed=True,
        reason=clean_reason,
        diff={
            "status": {"from": baseline["status"], "to": "exceptions"},
            "exception_codes": {"from": baseline_codes, "to": ["learned_policy_hold"]},
            "held_cents": {"from": 0, "to": amount_cents},
        },
        evidence=[source.id, target.id, policy.id, hold.id, ledger_id.strip()],
    )
    target.meta["learned_policy_application"]["audit_event_id"] = target_event.id
    flow.update(
        {
            "phase": "future_claim_held",
            "future_claim_id": target.id,
            "future_claim_work_item_id": hold.id,
            "future_claim_policy_id": policy.id,
            "future_claim_policy_version": policy.version,
            "future_claim_reporting_period": reporting_period,
            "future_claim_match_basis": match_basis,
            "future_claim_audit_event_id": target_event.id,
        }
    )
    source.log.append(
        f"Approved policy {policy.id} held independent October claim {target.id}"
    )
    sow.audit.append(
        actor=AI_CLAIMS.id,
        action="link_next_period_claim",
        subject=source.id,
        allowed=True,
        reason=clean_reason,
        diff={
            "phase": {"from": "policy_active", "to": "future_claim_held"},
            "future_claim_id": {"from": None, "to": target.id},
        },
        evidence=[source.id, target.id, policy.id, hold.id],
    )
    CLAIMS.upsert(target)
    CLAIMS.upsert(source)
    GUIDED_PERSISTENCE.save_claim(sow, target)
    GUIDED_PERSISTENCE.save_claim(sow, source)
    return _future_submission_result(
        sow,
        source=source,
        target=target,
        idempotent=False,
    )


def attempt_ai_approval(sow: SystemOfWork, *, claim_id: str, reason: str) -> dict[str, Any]:
    """Attempt approval as Jordan and return the access-control denial receipt."""
    clean_reason = _required_reason(reason)
    package = _package(claim_id)
    _restore(sow, package)
    flow = _flow(package)
    if flow.get("phase") != "future_claim_held":
        raise RuntimeError(f"AI approval cannot be attempted during phase {flow.get('phase')}")
    if package.status != "ready_for_approval":
        raise RuntimeError("claim still has unresolved exceptions")
    policy_id = flow.get("policy_id")
    if not policy_id or not sow.policies.get(policy_id) or sow.policies[policy_id].status != "active":
        raise RuntimeError("activate the proposed policy before testing the approval boundary")
    if flow.get("ai_approval_receipt"):
        raise RuntimeError("AI approval has already been attempted for this claim")

    prepare = _prepare_work_item(sow, package)
    try:
        # Empty transition reason preserves the authorization engine's denial reason.
        sow.approve(prepare.id, AI_CLAIMS, "")
    except Denied as exc:
        denial_event = sow.audit.denials()[-1]
        receipt = {
            "denied": True,
            "actor": AI_CLAIMS.id,
            "action": "approve",
            "claim_id": claim_id,
            "work_item_id": prepare.id,
            "requested_reason": clean_reason,
            "authorization_reason": exc.why,
            "audit_event_id": denial_event["id"],
            "at": denial_event["at"],
        }
    else:  # pragma: no cover - this is an invariant alarm, not a success path
        raise RuntimeError("authorization invariant failed: AI approval was unexpectedly allowed")

    flow.update({"phase": "ai_approval_denied", "ai_approval_receipt": receipt})
    package.log.append("Jordan approval attempt denied by the role boundary")
    event = sow.audit.append(
        actor=AI_CLAIMS.id,
        action="claim_ai_approval_receipt",
        subject=package.id,
        allowed=False,
        reason=receipt["authorization_reason"],
        diff={},
        evidence=[package.id, prepare.id, receipt["audit_event_id"]],
    )
    receipt["claim_audit_event_id"] = event.id
    CLAIMS.upsert(package)
    GUIDED_PERSISTENCE.save_claim(sow, package)
    return {
        "ok": True,
        "phase": flow["phase"],
        "denied": True,
        "denial_receipt": receipt,
        "claim": package.to_dict(),
    }


def approve_claim(sow: SystemOfWork, *, claim_id: str, reason: str) -> dict[str, Any]:
    """Approve a clean package as Priya after the AI denial has been proved."""
    clean_reason = _required_reason(reason)
    package = _package(claim_id)
    _restore(sow, package)
    flow = _flow(package)
    unresolved = _blocking_exceptions(package)
    if unresolved or package.status != "ready_for_approval":
        codes = sorted({str(ex.get("code")) for ex in unresolved})
        raise RuntimeError(f"claim has unresolved exceptions: {', '.join(codes) or package.status}")
    if not (flow.get("ai_approval_receipt") or {}).get("denied"):
        raise RuntimeError("prove the AI approval boundary before manager approval")
    if flow.get("phase") != "ai_approval_denied":
        raise RuntimeError(f"manager approval cannot occur during phase {flow.get('phase')}")
    policy_id = flow.get("policy_id")
    if not policy_id or not sow.policies.get(policy_id) or sow.policies[policy_id].status != "active":
        raise RuntimeError("the learned policy must be active before manager approval")
    if flow.get("manager_approval"):
        raise RuntimeError("the claim is already approved")

    prepare = _prepare_work_item(sow, package)
    if prepare.state != "PROPOSED":
        raise RuntimeError(f"claim preparation work is {prepare.state}, expected PROPOSED")
    sow.approve(prepare.id, FINANCE_MANAGER, clean_reason)
    package.status = "approved"
    approval = {
        "actor": FINANCE_MANAGER.id,
        "reason": clean_reason,
        "work_item_id": prepare.id,
        "at": now_iso(),
    }
    flow.update({"phase": "approved", "manager_approval": approval})
    package.meta["authorized_approvals"] = 1
    package.meta["unauthorized_approvals"] = 0
    package.log.append(f"Priya approved the claim: {clean_reason}")
    package.schedules_md = build_schedules(package)
    event = sow.audit.append(
        actor=FINANCE_MANAGER.id,
        action="claim_manager_approval",
        subject=package.id,
        allowed=True,
        reason=clean_reason,
        diff={"status": {"from": "ready_for_approval", "to": "approved"}},
        evidence=[package.id, prepare.id],
    )
    CLAIMS.upsert(package)
    GUIDED_PERSISTENCE.save_claim(sow, package)
    return {
        "ok": True,
        "phase": flow["phase"],
        "approval": approval,
        "audit_receipt": event.to_dict(),
        "claim": package.to_dict(),
    }


def guided_state(sow: SystemOfWork, claim_id: str) -> dict[str, Any]:
    """Small read model for clients that render the stepper."""
    package = _package(claim_id)
    _restore(sow, package)
    flow = _flow(package)
    if flow.get("phase") == "awaiting_decision":
        session = get_pending(claim_id) or recover_pending(sow, claim_id) or package.meta.get("loop_session") or {}
        prepare_id = str(session.get("prepare_wi_id") or "")
        question_id = str(session.get("ask_wi_id") or "")
        if not prepare_id or not question_id or not {
            prepare_id,
            question_id,
        }.issubset(sow.work_items):
            raise RuntimeError("guided review was reset; start a fresh claim")
    future_claim_id = flow.get("future_claim_id")
    future_claim = CLAIMS.get(str(future_claim_id)) if future_claim_id else None
    future_work_item_id = str(flow.get("future_claim_work_item_id") or "")
    future_work_item = sow.work_items.get(future_work_item_id)
    return {
        "claim_id": claim_id,
        "phase": flow.get("phase"),
        "workflow": flow,
        "policy": sow.policies[str(flow["policy_id"])].to_dict() if flow.get("policy_id") in sow.policies else None,
        "unresolved_exceptions": _blocking_exceptions(package),
        "question": (package.meta.get("rule_refresh") or {}).get("suggested_question") or CATERING_QUESTION,
        "claim": package.to_dict(),
        "future_claim": future_claim.to_dict() if future_claim else None,
        "future_claim_work_item": future_work_item.to_dict() if future_work_item else None,
    }
