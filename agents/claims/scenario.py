"""Answer-key demo: Hyphenate Claims learning loop (manager no → precedent → policy)."""

from __future__ import annotations

from typing import Any

from claims.corpus import corpus_summary
from claims.learning_loop import (
    MANAGER_NO,
    resume_claims_learning,
    run_claims_learning_demo,
    start_claims_learning,
)
from claims.pipeline import run_demo_claim
from sow.scoring import score_run


ANSWER_KEY = {
    "product": "SwarmCFO Claims",
    "customer": "Meridian Bookkeeping — fractional CFO for Bay Area Workforce Collaborative",
    "cast": {
        "claims_agent": "Jordan",
        "finance_manager": "Priya Shah",
        "nonprofit": "Bay Area Workforce Collaborative",
    },
    "mission": (
        "Prepare September reimbursement for Award FOA-ETA-25-01. Ask Priya about ambiguous costs. "
        "Learn from a no. Improve October. Do not submit. Do not alter the ledger."
    ),
    "hyphenate_loop": [
        "Jordan prepares revision 1",
        "Flags four messy exceptions in plain language",
        "Asks Priya about the $860 catering charge",
        "Priya: No — staff celebration. Exclude it.",
        "Jordan builds revision 2",
        "Correction saved as precedent",
        "Policy proposed + Priya approves",
        "October catering auto-held",
        "Jordan approve → DENIED",
        "Priya approves the package",
        "Audit shows the whole conversation as diffs",
    ],
    "objective_results": {
        "excluded_usd": 8160.0,
        "receipt_attached_usd": 124.0,
        "eligible_reimbursement_usd": 28135.0,
        "critical_exceptions": "4 → 0",
        "unauthorized_approvals": 0,
    },
    "features": [
        "Jordan asks; Priya decides",
        "Manager no → revision → precedent → policy",
        "Next-case auto-hold",
        "Denied agent approval (limits in code)",
        "Append-only audit with revision diffs",
        "Rejection-risk priors from public corpora",
    ],
    "tracks": {
        "01_real_enough": "Real workforce-grant GL with planted mess, not a toy ledger",
        "02_would_you_hire_it": "RBAC deny + queryable audit + human in the loop",
        "03_something_new": "Nonprofit claims learning loop (not bakery short-wire clone)",
        "04_wow_moment": "$8,160 kept off the award + October held by learned policy",
    },
}


def _with_viz(result: dict[str, Any], sow: Any | None) -> dict[str, Any]:
    risk = result.get("risk") or {}
    corpus = corpus_summary()
    viz = {
        "score": int(risk.get("score") or 0),
        "band": risk.get("band") or "low",
        "recommendation": risk.get("recommendation") or "",
        "drivers": list(risk.get("drivers") or []),
        "exceptions": (result.get("claim") or {}).get("exceptions") or [],
        "corpus": {
            "fac_findings": corpus.get("fac_findings"),
            "ca_denied_rows": corpus.get("ca_denied_rows"),
            "grants_gov_rejection_rows": corpus.get("grants_gov_rejection_rows"),
            "ca_grants_awards": corpus.get("ca_grants_awards"),
            "irs990_index_rows": corpus.get("irs990_index_rows"),
            "propublica_orgs": corpus.get("propublica_orgs"),
        },
        "nonprofit": (result.get("claim") or {}).get("nonprofit"),
        "claimed_cents": ((result.get("claim") or {}).get("totals") or {}).get("eligible_cents")
        or ((result.get("claim") or {}).get("totals") or {}).get("claimed_cents"),
        "checks": result.get("checks"),
        "results": result.get("results"),
        "story": result.get("story"),
    }
    out = {
        **result,
        "answer_key": ANSWER_KEY,
        "corpus": corpus,
        "viz": viz,
        "log": (result.get("claim") or {}).get("log") or [],
    }
    if sow is not None:
        out["hyphenate"] = score_run(sow)
    return out


def run_claims_demo(
    sow: Any | None = None,
    *,
    phase: str = "full",
    claim_id: str | None = None,
    answer: str | None = None,
) -> dict[str, Any]:
    """
    phase:
      full — one-shot learning loop (CI / quick check)
      start — pause at Priya's question (stage demo)
      resume — continue after manager answer
    """
    if sow is None:
        shallow = run_demo_claim(None)
        return {
            **shallow,
            "ok": False,
            "score": 0,
            "checks": {"requires_sow": False},
            "answer_key": ANSWER_KEY,
            "corpus": corpus_summary(),
        }

    if phase == "start":
        return _with_viz(start_claims_learning(sow), sow)
    if phase == "resume":
        return _with_viz(
            resume_claims_learning(sow, claim_id=claim_id, answer=answer or MANAGER_NO),
            sow,
        )
    return _with_viz(run_claims_learning_demo(sow, interactive_pause=False), sow)
