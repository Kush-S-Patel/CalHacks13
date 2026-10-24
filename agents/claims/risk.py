"""
Rejection / findings risk score for a reimbursement claim package.

Priors from:
  - FAC Single Audit finding types + questioned costs (strongest public proxy)
  - Covered CA denial taxonomy rates (incorrect submission/billing, ineligibility, duplicates)
  - Grants.gov-shaped submission rejection classes (grantor-only limitation documented)
  - CA Grants Portal awards (funding relationships / cancel notes — soft context)
  - ProPublica 990 financials (capacity / burn-rate enrichment — soft context)

Arithmetic is deterministic in code — LLMs do not invent the score.
"""

from __future__ import annotations

from typing import Any

from claims.corpus import (
    EXCEPTION_TO_DRIVERS,
    awards_for_name,
    corpus_summary,
    load_fac_findings,
    load_grants_gov_rejections,
    propublica_for_name,
)
from claims.models import ClaimPackage, RiskScore


def _band(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 35:
        return "moderate"
    return "low"


def _ca_prior(category: str) -> float:
    summary = corpus_summary()
    rates = summary.get("ca_category_avg_rates") or {}
    return float(rates.get(category) or 0.02)


def _fac_weight(type_requirement: str) -> float:
    fac = load_fac_findings()
    if not fac:
        return 0.1
    hits = [r for r in fac if (r.get("type_requirement") or "") == type_requirement]
    if not hits:
        return 0.08
    # material weakness / modified opinion bump
    mw = sum(1 for r in hits if str(r.get("is_material_weakness", "")).upper().startswith("Y"))
    qc = 0
    for r in hits:
        try:
            qc += int(float(r.get("questioned_costs") or 0))
        except ValueError:
            pass
    base = 0.12 + 0.08 * (mw / max(1, len(hits)))
    if qc > 10_000:
        base += 0.1
    elif qc > 0:
        base += 0.05
    return min(0.45, base)


def _gg_weight(rejection_class: str) -> float:
    gg = load_grants_gov_rejections()
    if not gg:
        return 0.05
    n = sum(1 for r in gg if r.get("rejection_class") == rejection_class)
    return min(0.25, 0.05 + 0.04 * n)


def score_claim_risk(package: ClaimPackage) -> RiskScore:
    drivers: list[dict[str, Any]] = []
    score = 8  # baseline friction for any federal/state reimbursement

    # Exception-driven risk
    codes: list[str] = []
    for m in package.matches:
        codes.extend(c for c in m.exception_codes if c != "excluded_from_claim")
    for ex in package.exceptions:
        if isinstance(ex, dict) and ex.get("code"):
            codes.append(str(ex["code"]))
        elif isinstance(ex, str):
            # best-effort
            pass
    codes = list(dict.fromkeys(codes))

    for code in codes:
        if code == "excluded_from_claim":
            continue
        mapped = EXCEPTION_TO_DRIVERS.get(code, [])
        bump = 6
        detail: dict[str, Any] = {"exception": code, "sources": []}
        for driver in mapped:
            if driver in {
                "incorrect_submission",
                "incorrect_billing",
                "ineligibility",
                "duplicate_claims",
            }:
                prior = _ca_prior(driver)
                add = int(round(prior * 100 * 1.8)) + 4
                bump += add
                detail["sources"].append({"corpus": "ca_denied_claims", "category": driver, "prior_rate": prior, "points": add})
            elif driver in {
                "Allowable Costs/Cost Principles",
                "Eligibility",
                "Reporting",
                "Period of Performance",
                "Procurement and Suspension and Debarment",
            }:
                w = _fac_weight(driver)
                add = int(round(w * 100))
                bump += add
                detail["sources"].append({"corpus": "fac_findings", "type_requirement": driver, "weight": w, "points": add})
            else:
                w = _gg_weight(driver)
                add = int(round(w * 80))
                bump += add
                detail["sources"].append({"corpus": "grants_gov_shaped", "rejection_class": driver, "weight": w, "points": add})
        score += min(28, bump)
        drivers.append(detail)

    # Coverage: unmatched / low-confidence lines (ignore lines already excluded from claim)
    active = [m for m in package.matches if "excluded_from_claim" not in m.exception_codes]
    low_conf = [m for m in active if m.confidence < 0.55]
    missing_ev = [m for m in active if not m.evidence_ids]
    if missing_ev:
        add = min(20, 4 * len(missing_ev))
        score += add
        drivers.append(
            {
                "exception": "missing_evidence_links",
                "count": len(missing_ev),
                "points": add,
                "sources": [{"corpus": "fac_findings", "note": "Allowable costs require supporting documentation"}],
            }
        )
    if low_conf:
        add = min(12, 3 * len(low_conf))
        score += add
        drivers.append({"exception": "low_match_confidence", "count": len(low_conf), "points": add, "sources": []})

    # GL reconciliation gap
    claimed = int(package.totals.get("claimed_cents") or 0)
    gl = int(package.totals.get("gl_cents") or 0)
    if gl and abs(claimed - gl) > 100:
        gap = abs(claimed - gl)
        add = 10 + min(15, gap // 50000)
        score += add
        drivers.append(
            {
                "exception": "unreconciled_gl",
                "gap_cents": gap,
                "points": add,
                "sources": [{"corpus": "fac_findings", "type_requirement": "Reporting"}],
            }
        )

    # Budget line overruns
    budget = package.award.budget_lines or {}
    spent: dict[str, int] = {}
    for m in package.matches:
        if m.exception_codes and "budget_overrun" in m.exception_codes:
            continue
        spent[m.budget_line] = spent.get(m.budget_line, 0) + m.amount_cents
    for line, cap in budget.items():
        if spent.get(line, 0) > cap:
            add = 12
            score += add
            drivers.append(
                {
                    "exception": "budget_overrun",
                    "budget_line": line,
                    "spent_cents": spent[line],
                    "cap_cents": cap,
                    "points": add,
                    "sources": [{"corpus": "fac_findings", "type_requirement": "Allowable Costs/Cost Principles"}],
                }
            )

    # Historical nonprofit FAC hits by name fragment
    fac = load_fac_findings()
    name = (package.nonprofit or "").lower()
    hist = [r for r in fac if name and name[:12] in (r.get("auditee_name") or "").lower()]
    if hist:
        add = 8 + 4 * len(hist)
        score += add
        drivers.append(
            {
                "exception": "prior_fac_findings",
                "count": len(hist),
                "points": add,
                "sources": [{"corpus": "fac_findings", "report_ids": [r.get("report_id") for r in hist]}],
            }
        )

    # CA Grants Portal: prior awards / cancel notes for similar recipient names
    ca_hits = awards_for_name(package.nonprofit or "")
    if ca_hits:
        cancel_hits = [r for r in ca_hits if (r.get("AwardCancellingNotes") or "").strip()]
        underused = []
        for r in ca_hits:
            awarded = float(r.get("_award_amount") or 0)
            used = float(r.get("_award_used") or 0)
            if awarded > 0 and used > 0 and used / awarded < 0.15:
                underused.append(r)
        if cancel_hits:
            add = min(10, 4 + 2 * len(cancel_hits))
            score += add
            drivers.append(
                {
                    "exception": "ca_award_cancel_notes",
                    "count": len(cancel_hits),
                    "points": add,
                    "sources": [
                        {
                            "corpus": "ca_grants",
                            "note": "Award cancelling notes are not reimbursement denials; soft friction prior",
                            "recipients": [r.get("RecipientName") for r in cancel_hits[:5]],
                        }
                    ],
                }
            )
        elif underused:
            add = 3
            score += add
            drivers.append(
                {
                    "exception": "ca_award_low_drawdown",
                    "count": len(underused),
                    "points": add,
                    "sources": [{"corpus": "ca_grants", "note": "Low award utilization — reporting / drawdown friction signal"}],
                }
            )
        else:
            drivers.append(
                {
                    "exception": "ca_award_history",
                    "count": len(ca_hits),
                    "points": 0,
                    "sources": [
                        {
                            "corpus": "ca_grants",
                            "note": "Prior CA Grants Portal awards for similar recipient names (context only)",
                            "sample_agencies": list({r.get("AgencyDept") for r in ca_hits[:5]}),
                        }
                    ],
                }
            )

    # ProPublica 990 enrichment: extreme expense/revenue ratio → soft capacity prior
    pp = propublica_for_name(package.nonprofit or "")
    if pp and pp.get("_expense_ratio") is not None:
        ratio = float(pp["_expense_ratio"])
        if ratio > 1.15 or ratio < 0.35:
            add = 4
            score += add
            drivers.append(
                {
                    "exception": "990_expense_ratio_outlier",
                    "expense_ratio": round(ratio, 3),
                    "points": add,
                    "sources": [
                        {
                            "corpus": "propublica",
                            "ein": pp.get("ein"),
                            "name": pp.get("name"),
                            "note": "Digitized 990 capacity signal — not a claim denial",
                        }
                    ],
                }
            )
        else:
            drivers.append(
                {
                    "exception": "990_profile_matched",
                    "expense_ratio": round(ratio, 3),
                    "points": 0,
                    "sources": [
                        {
                            "corpus": "propublica",
                            "ein": pp.get("ein"),
                            "name": pp.get("name"),
                            "revenue": pp.get("_revenue"),
                            "expenses": pp.get("_expenses"),
                        }
                    ],
                }
            )

    score = max(0, min(100, score))
    band = _band(score)  # type: ignore[assignment]

    if band == "critical":
        rec = "Do not submit — remediate exceptions and re-score. High likelihood of rejection or audit finding."
    elif band == "high":
        rec = "Hold for finance manager: clear missing evidence and duplicates before submission."
    elif band == "moderate":
        rec = "Submit only after documented exception clearance; attach evidence index."
    else:
        rec = "Package appears supportable; finance manager can approve for submission."

    return RiskScore(
        score=score,
        band=band,  # type: ignore[arg-type]
        drivers=drivers,
        corpus_priors=corpus_summary(),
        recommendation=rec,
    )
