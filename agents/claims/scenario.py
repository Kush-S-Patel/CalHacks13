"""Answer-key demo: Hyphenate Claims learning loop (manager no → precedent → policy)."""

from __future__ import annotations

from typing import Any

from claims.corpus import corpus_summary
from claims.learning_loop import run_claims_learning_demo
from claims.pipeline import run_demo_claim


ANSWER_KEY = {
    "product": "SwarmCFO Claims",
    "customer": "Outsourced nonprofit bookkeeping / fractional-CFO firm",
    "mission": (
        "Prepare September reimbursement for Award FOA-ETA-25-01 — ask the manager about "
        "ambiguous costs, learn from a no, improve the next case. Do not submit. Do not alter the ledger."
    ),
    "agents": [
        "Claims Agent (ai_claims) — prepare, ask, propose policy; never approve",
        "Finance Manager (human_finance_manager) — answer, approve claim + policy",
        "Risk priors — FAC / CA denied / Grants.gov / CA awards / 990",
    ],
    "hyphenate_loop": [
        "Claims Agent prepares revision 1",
        "Detects four critical exceptions",
        "Asks about the ambiguous $860 catering charge",
        'Manager answers: "No—staff celebration. Exclude it."',
        "Correction creates revision 2",
        "Correction saved as precedent",
        "System proposes policy for future staff celebrations",
        "Similar next-month expense auto-held by that policy",
        "Claims Agent approve → DENIED",
        "Finance Manager approves",
        "Audit shows question, answer, revision diff, policy, deny, approve",
    ],
    "objective_results": {
        "excluded_usd": 8160.0,
        "receipt_attached_usd": 124.0,
        "eligible_reimbursement_usd": 28135.0,
        "critical_exceptions": "4 → 0",
        "unauthorized_approvals": 0,
    },
    "data_priors": [
        "FAC Single Audit findings / questioned costs",
        "Covered CA denied-claims taxonomy",
        "Grants.gov-shaped submission failures",
        "California Grants Portal awards",
        "IRS 990 TEOS index + ProPublica financials",
    ],
    "features": [
        "Governed Claims Agent + Finance Manager roles",
        "Manager ask → no → revision 2",
        "Precedent + policy generalization",
        "Next-case auto-hold from learned policy",
        "Denied agent approval (limits in code)",
        "Append-only audit with revision diffs",
        "Rejection risk score grounded in public corpora",
    ],
}


def run_claims_demo(sow: Any | None = None) -> dict[str, Any]:
    """Primary product demo = learning loop (requires SoW). Falls back to shallow package-only."""
    if sow is None:
        shallow = run_demo_claim(None)
        return {
            **shallow,
            "ok": False,
            "score": 0,
            "checks": {"requires_sow": False},
            "answer_key": ANSWER_KEY,
            "note": "Pass SystemOfWork for the Hyphenate learning loop",
            "corpus": corpus_summary(),
        }

    result = run_claims_learning_demo(sow)
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
        "claimed_cents": ((result.get("claim") or {}).get("totals") or {}).get("eligible_cents"),
        "checks": result.get("checks"),
        "results": result.get("results"),
        "story": result.get("story"),
    }
    return {
        **result,
        "answer_key": ANSWER_KEY,
        "corpus": corpus,
        "viz": viz,
        "log": (result.get("claim") or {}).get("log") or [],
    }
