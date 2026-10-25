"""Durable pending-session helpers for the Claims learning loop."""

from __future__ import annotations

from typing import Any

from claims.models import ClaimPackage
from claims.store import CLAIMS
from sow.store import SystemOfWork

# claim_id → session handles (also mirrored onto claim.meta["loop_session"])
_PENDING: dict[str, dict[str, Any]] = {}


def clear_all_pending() -> None:
    _PENDING.clear()
    for p in CLAIMS.packages.values():
        if p.meta.get("awaiting_manager") or p.meta.get("loop_session"):
            p.meta["awaiting_manager"] = False
            p.meta.pop("loop_session", None)
            CLAIMS.upsert(p)


def save_pending(claim_id: str, session: dict[str, Any], package: ClaimPackage) -> None:
    payload = {
        "prepare_wi_id": session["prepare_wi_id"],
        "ask_wi_id": session["ask_wi_id"],
        "claim_id": claim_id,
        "critical": list(session.get("critical") or []),
        "story": list(session.get("story") or []),
    }
    _PENDING[claim_id] = payload
    package.meta["awaiting_manager"] = True
    package.meta["loop_session"] = {
        "prepare_wi_id": payload["prepare_wi_id"],
        "ask_wi_id": payload["ask_wi_id"],
        "critical": payload["critical"],
    }
    CLAIMS.upsert(package)


def pop_pending(claim_id: str) -> None:
    _PENDING.pop(claim_id, None)
    package = CLAIMS.get(claim_id)
    if package:
        package.meta["awaiting_manager"] = False
        package.meta.pop("loop_session", None)
        CLAIMS.upsert(package)


def get_pending(claim_id: str | None = None) -> dict[str, Any] | None:
    if claim_id and claim_id in _PENDING:
        return _PENDING[claim_id]
    if claim_id is None and len(_PENDING) == 1:
        return next(iter(_PENDING.values()))
    return None


def list_pending() -> list[dict[str, Any]]:
    return [dict(v) for v in _PENDING.values()]


def recover_pending(sow: SystemOfWork, claim_id: str | None = None) -> dict[str, Any] | None:
    """Rebuild in-memory session from claim meta and/or open NEEDS_INFO work."""
    if claim_id and claim_id in _PENDING:
        return _PENDING[claim_id]

    candidates: list[str] = []
    if claim_id:
        candidates.append(claim_id)
    else:
        candidates.extend(list(_PENDING.keys()))
        for p in CLAIMS.packages.values():
            if p.meta.get("awaiting_manager") and p.id not in candidates:
                candidates.append(p.id)
        for w in sow.work_items.values():
            if w.kind == "claim_question" and w.state == "NEEDS_INFO":
                cid = str(w.payload.get("claim_id") or w.subject)
                if cid not in candidates:
                    candidates.append(cid)

    for cid in candidates:
        package = CLAIMS.get(cid)
        if not package:
            continue
        meta_sess = package.meta.get("loop_session") or {}
        ask_id = meta_sess.get("ask_wi_id")
        prep_id = meta_sess.get("prepare_wi_id")
        ask = sow.work_items.get(ask_id) if ask_id else None
        prep = sow.work_items.get(prep_id) if prep_id else None
        if not ask or ask.state != "NEEDS_INFO":
            ask = next(
                (
                    w
                    for w in sow.work_items.values()
                    if w.kind == "claim_question"
                    and w.state == "NEEDS_INFO"
                    and (w.payload.get("claim_id") == cid or w.subject == cid)
                ),
                None,
            )
        if not prep:
            prep = next(
                (
                    w
                    for w in sow.work_items.values()
                    if w.kind == "claim_prepare"
                    and w.state == "PROPOSED"
                    and (w.payload.get("claim_id") == cid or w.subject == cid)
                ),
                None,
            )
        if ask and prep and package:
            session = {
                "prepare_wi_id": prep.id,
                "ask_wi_id": ask.id,
                "claim_id": cid,
                "critical": list(meta_sess.get("critical") or []),
                "story": list(_PENDING.get(cid, {}).get("story") or []),
            }
            _PENDING[cid] = session
            return session
    return None


def completed_result_from_claim(package: ClaimPackage) -> dict[str, Any] | None:
    """Idempotent resume if loop already finished."""
    if package.status == "approved" and package.meta.get("revision") == 2:
        totals = package.totals or {}
        return {
            "ok": True,
            "awaiting_manager": False,
            "phase": "complete",
            "idempotent": True,
            "score": 100,
            "claim": package.to_dict(),
            "results": {
                "excluded_usd": (totals.get("excluded_cents") or 0) / 100,
                "eligible_reimbursement_usd": (totals.get("eligible_cents") or totals.get("claimed_cents") or 0)
                / 100,
                "receipt_attached_usd": (totals.get("receipt_attached_cents") or 0) / 100,
                "critical_exceptions_after": 0,
                "revision": 2,
            },
            "outcome": "Already completed — revision 2 approved (idempotent resume)",
            "talk_track": "This claim already finished the learning loop.",
        }
    return None
