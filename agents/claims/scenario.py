"""Answer-key demo: nonprofit monthly reimbursement package + rejection risk."""

from __future__ import annotations

from typing import Any

from claims.corpus import corpus_summary
from claims.pipeline import run_demo_claim


ANSWER_KEY = {
    "product": "SwarmCFO Claims",
    "customer": "Outsourced nonprofit bookkeeping / fractional CFO firm",
    "mission": "Prepare September reimbursement for Award FOA-ETA-25-01 — do not submit or alter ledger",
    "agents": [
        "Award analyst → rulebook",
        "Transaction matcher → GL↔evidence",
        "Compliance reviewer → exceptions",
        "Deterministic validation → totals/recon",
        "Claim preparer + risk scorer → package",
    ],
    "data_priors": [
        "FAC Single Audit findings / questioned costs",
        "Covered CA denied-claims taxonomy (incorrect submission/billing, ineligibility, duplicates)",
        "Grants.gov Rejection Report–shaped submission failures (grantor-only; synthetic samples)",
        "California Grants Portal award–awardee relationships",
        "IRS Form 990 TEOS index + ProPublica digitized financials",
    ],
    "features": [
        "Award analyst rulebook",
        "Transaction matcher (GL ↔ evidence)",
        "Compliance exceptions",
        "Deterministic totals / recon / budget caps",
        "Rejection risk score 0–100 with corpus drivers",
        "Nonprofit enrichment (CA awards / 990 / ProPublica)",
    ],
    "expected": {
        "duplicate_flagged": True,
        "missing_docs_flagged": True,
        "pop_flagged": True,
        "unallowable_flagged": True,
        "risk_score_present": True,
        "package_nonempty": True,
        "corpus_loaded": True,
    },
}


def _viz_payload(claim: dict[str, Any], risk: dict[str, Any], corpus: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    """Chart-ready payload for UI gauges / bars."""
    drivers = list(risk.get("drivers") or [])
    return {
        "score": int(risk.get("score") or 0),
        "band": risk.get("band") or "low",
        "recommendation": risk.get("recommendation") or "",
        "drivers": drivers,
        "exceptions": claim.get("exceptions") or [],
        "corpus": {
            "fac_findings": corpus.get("fac_findings"),
            "ca_denied_rows": corpus.get("ca_denied_rows"),
            "grants_gov_rejection_rows": corpus.get("grants_gov_rejection_rows"),
            "ca_grants_awards": corpus.get("ca_grants_awards"),
            "irs990_index_rows": corpus.get("irs990_index_rows"),
            "propublica_orgs": corpus.get("propublica_orgs"),
            "ca_grants_top_agencies": corpus.get("ca_grants_top_agencies"),
            "fac_type_counts": corpus.get("fac_type_counts"),
        },
        "nonprofit": claim.get("nonprofit"),
        "claimed_cents": (claim.get("totals") or {}).get("claimed_cents"),
        "checks": checks,
        "pipeline": ANSWER_KEY["features"],
    }


def run_claims_demo(sow: Any | None = None) -> dict[str, Any]:
    result = run_demo_claim(sow)
    claim = result["claim"]
    risk = result.get("risk") or {}
    corpus = corpus_summary()
    codes = {ex.get("code") for ex in claim.get("exceptions") or [] if isinstance(ex, dict)}
    checks = {
        "duplicate_flagged": "duplicate_expense" in codes,
        "missing_docs_flagged": bool({"missing_receipt", "missing_payroll"} & codes),
        "pop_flagged": "period_of_performance" in codes,
        "unallowable_flagged": "ineligible_participant" in codes,
        "risk_score_present": isinstance(risk.get("score"), int),
        "package_nonempty": len(claim.get("schedules_md") or "") > 200,
        "corpus_loaded": int(corpus.get("fac_findings") or 0) > 0 and int(corpus.get("ca_grants_awards") or 0) > 0,
    }
    score = int(100 * sum(1 for v in checks.values() if v) / max(1, len(checks)))
    viz = _viz_payload(claim, risk, corpus, checks)
    return {
        "ok": all(checks.values()),
        "score": score,
        "checks": checks,
        "answer_key": ANSWER_KEY,
        "claim": claim,
        "risk": risk,
        "corpus": corpus,
        "viz": viz,
        "log": claim.get("log") or [],
    }
