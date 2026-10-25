"""Live rule retrieval (Apify) and interpretation (Claude) for one claim review.

Fails closed: configuration errors, Actor failures, schema/quote problems, and
low-confidence interpretations are recorded as receipts but do not silently fall
back to bundled rule text.
"""

from __future__ import annotations

from typing import Any

from claims.apify_source import ApifySourceError, fetch_rule_source
from claims.guided_persistence import GUIDED_PERSISTENCE
from claims.learning_loop import CATERING_QUESTION
from claims.rule_interpreter import RuleInterpretation, RuleInterpretationError, interpret_claim_rule
from claims.store import CLAIMS
from config import settings
from claims.models import now_iso
from sow.models import AI_CLAIMS
from sow.store import SystemOfWork

DEFAULT_RULE_SOURCE_URL = (
    "https://www.govinfo.gov/content/pkg/CFR-2026-title2-vol01/xhtml/"
    "CFR-2026-title2-vol01-part200-subpartE.html"
)
MIN_INTERPRETATION_CONFIDENCE = 0.75


def _package(claim_id: str):
    package = CLAIMS.get(claim_id)
    if not package:
        raise KeyError(f"unknown claim {claim_id}")
    return package


def _restore(sow: SystemOfWork, package: Any) -> None:
    from claims.guided_flow import _restore as guided_restore

    guided_restore(sow, package)


def refresh_claim_rule(
    sow: SystemOfWork,
    claim_id: str,
    *,
    source_url: str | None = None,
) -> dict[str, Any]:
    """Run Apify + Claude for the claim's governing rule and store both receipts."""

    package = _package(claim_id)
    _restore(sow, package)
    if (package.meta.get("guided_flow") or {}).get("decision"):
        raise ValueError("Refresh the governing rule before recording the manager decision")

    existing = package.meta.get("rule_source") if isinstance(package.meta.get("rule_source"), dict) else {}
    url = (source_url or existing.get("url") or DEFAULT_RULE_SOURCE_URL).strip()
    previous_hash = existing.get("content_hash")
    if previous_hash is not None:
        previous_hash = str(previous_hash)

    receipts: dict[str, Any] = dict(package.meta.get("provider_receipts") or {})
    refresh_meta: dict[str, Any] = {
        "source_url": url,
        "model": settings.claude_model,
        "attempted_at": now_iso(),
    }

    try:
        source = fetch_rule_source(url, previous_hash=previous_hash)
    except ApifySourceError as exc:
        refresh_meta["status"] = "source_failed"
        refresh_meta["error"] = str(exc)
        package.meta["rule_refresh"] = refresh_meta
        sow.audit.append(
            actor=AI_CLAIMS.id,
            action="refresh_rule_source",
            subject=package.id,
            allowed=False,
            reason=str(exc),
            diff={"status": "source_failed", "source_url": url},
            evidence=[package.id],
        )
        CLAIMS.upsert(package)
        GUIDED_PERSISTENCE.save_claim(sow, package)
        raise ValueError(f"rule source refresh failed: {exc}") from exc

    receipts["apify"] = source.to_dict()
    refresh_meta["apify_run_id"] = source.run_id
    refresh_meta["apify_dataset_id"] = source.dataset_id
    refresh_meta["fetched_at"] = source.fetched_at

    try:
        interpretation = interpret_claim_rule(
            review_question=CATERING_QUESTION,
            clean_text=source.clean_text,
            source_url=source.source_url,
        )
    except RuleInterpretationError as exc:
        receipts["claude"] = {"error": exc.code, "message": str(exc)}
        refresh_meta["status"] = "interpretation_failed"
        refresh_meta["error_code"] = exc.code
        package.meta["provider_receipts"] = receipts
        package.meta["rule_refresh"] = refresh_meta
        sow.audit.append(
            actor=AI_CLAIMS.id,
            action="refresh_rule_source",
            subject=package.id,
            allowed=False,
            reason=str(exc),
            diff={"status": "interpretation_failed", "code": exc.code},
            evidence=[package.id, source.run_id],
        )
        CLAIMS.upsert(package)
        GUIDED_PERSISTENCE.save_claim(sow, package)
        raise ValueError(str(exc)) from exc

    receipts["claude"] = {**interpretation.model_dump(), "model": settings.claude_model, "live": True}
    refresh_meta["confidence"] = interpretation.confidence
    refresh_meta["needs_human"] = interpretation.needs_human

    applied = (
        not interpretation.needs_human
        and interpretation.confidence >= MIN_INTERPRETATION_CONFIDENCE
    )
    refresh_meta["status"] = "applied" if applied else "needs_human"

    if applied:
        package.meta["rule_source"] = {
            "title": source.title,
            "url": source.source_url,
            "quote": interpretation.exact_quote,
            "rule": interpretation.rule,
            "provenance": (
                f"Apify Actor {source.actor_id} · run {source.run_id} · "
                f"Claude {settings.claude_model}"
            ),
            "live_refresh": True,
            "fetched_at": source.fetched_at,
            "content_hash": source.content_hash,
            "changed": source.changed,
            "previous_hash": source.previous_hash,
            "apify_run_id": source.run_id,
            "apify_dataset_id": source.dataset_id,
            "interpretation_confidence": interpretation.confidence,
        }
    else:
        refresh_meta["suggested_question"] = interpretation.suggested_question

    package.meta["provider_receipts"] = receipts
    package.meta["rule_refresh"] = refresh_meta
    sow.audit.append(
        actor=AI_CLAIMS.id,
        action="refresh_rule_source",
        subject=package.id,
        allowed=applied,
        reason=(
            "Live source and Claude interpretation stored on the claim"
            if applied
            else "Interpretation requires human review before replacing bundled rule text"
        ),
        diff={
            "status": refresh_meta["status"],
            "content_hash": source.content_hash,
            "run_id": source.run_id,
        },
        evidence=[package.id, source.run_id, source.dataset_id],
    )
    CLAIMS.upsert(package)
    GUIDED_PERSISTENCE.save_claim(sow, package)

    return {
        "ok": True,
        "status": refresh_meta["status"],
        "claim_id": claim_id,
        "claim": package.to_dict(),
        "source_receipt": receipts["apify"],
        "interpretation": receipts["claude"],
        "rule_source": package.meta.get("rule_source"),
    }


def claim_audit_chain(sow: SystemOfWork, claim_id: str) -> dict[str, Any]:
    """Reproduce append-only audit events for one claim (restart-safe)."""

    package = _package(claim_id)
    _restore(sow, package)

    by_id: dict[str, dict[str, Any]] = {}
    for row in GUIDED_PERSISTENCE.audit_rows(claim_id):
        event_id = str(row.get("id") or "")
        if event_id:
            by_id[event_id] = row

    for event in sow.audit.all():
        if claim_id == event.get("subject") or claim_id in (event.get("evidence") or []):
            event_id = str(event.get("id") or "")
            if event_id and event_id not in by_id:
                by_id[event_id] = event

    events = sorted(by_id.values(), key=lambda row: (str(row.get("at") or ""), str(row.get("id") or "")))
    return {
        "claim_id": claim_id,
        "count": len(events),
        "events": events,
    }
