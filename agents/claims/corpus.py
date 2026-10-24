"""Load FAC / CA denied / Grants.gov / CA awards / IRS 990 / ProPublica corpora."""

from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2] / "data" / "train_data" / "claims"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _money(raw: str | None) -> float:
    if not raw:
        return 0.0
    s = re.sub(r"[^\d.\-]", "", str(raw))
    if not s or s in {".", "-", "-."}:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


@lru_cache(maxsize=1)
def load_fac_findings() -> list[dict[str, Any]]:
    rows = _read_csv(ROOT / "fac" / "findings_sample.csv")
    api = ROOT / "fac" / "findings_api_sample.json"
    if api.exists():
        try:
            data = json.loads(api.read_text(encoding="utf-8"))
            if isinstance(data, list):
                rows.extend({str(k): str(v) for k, v in row.items()} for row in data)
        except json.JSONDecodeError:
            pass
    return rows


@lru_cache(maxsize=1)
def load_ca_denied() -> list[dict[str, Any]]:
    return _read_csv(ROOT / "ca_denied" / "ca_denied_claims_aggregate.csv")


@lru_cache(maxsize=1)
def load_grants_gov_rejections() -> list[dict[str, Any]]:
    return _read_csv(ROOT / "grants_gov" / "rejection_report_shaped_sample.csv")


@lru_cache(maxsize=1)
def load_ca_grants() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((ROOT / "ca_grants").glob("*.csv")):
        for r in _read_csv(path):
            r["_source_file"] = path.name
            r["_award_amount"] = _money(r.get("TotalAwardAmount"))
            r["_award_used"] = _money(r.get("TotalAwardUsed"))
            rows.append(r)
    return rows


@lru_cache(maxsize=1)
def load_irs990_index() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((ROOT / "irs990").glob("index_*.csv")):
        for r in _read_csv(path):
            r["_source_file"] = path.name
            rows.append(r)
    return rows


@lru_cache(maxsize=1)
def load_propublica_orgs() -> list[dict[str, Any]]:
    path = ROOT / "propublica" / "org_financials.csv"
    out: list[dict[str, Any]] = []
    for r in _read_csv(path):
        rev = _money(r.get("revenue"))
        exp = _money(r.get("expenses"))
        assets = _money(r.get("assets"))
        out.append(
            {
                **r,
                "_revenue": rev,
                "_expenses": exp,
                "_assets": assets,
                "_expense_ratio": (exp / rev) if rev > 0 else None,
            }
        )
    return out


def lookup_nonprofit(*, q: str | None = None, ein: str | None = None, limit: int = 20) -> dict[str, Any]:
    """Enrichment lookup across ProPublica, IRS index, and CA Grants Portal awards."""
    ein_digits = re.sub(r"\D", "", ein or "")
    needle = (q or "").strip().lower()
    pp = load_propublica_orgs()
    irs = load_irs990_index()
    awards = load_ca_grants()

    orgs: list[dict[str, Any]] = []
    for o in pp:
        o_ein = re.sub(r"\D", "", o.get("ein") or "")
        name = (o.get("name") or "").lower()
        if ein_digits and o_ein != ein_digits:
            continue
        if needle and needle not in name and needle not in o_ein:
            continue
        orgs.append(
            {
                "ein": o.get("ein"),
                "name": o.get("name"),
                "city": o.get("city"),
                "state": o.get("state"),
                "ntee_code": o.get("ntee_code"),
                "revenue": o.get("_revenue"),
                "expenses": o.get("_expenses"),
                "assets": o.get("_assets"),
                "expense_ratio": o.get("_expense_ratio"),
                "tax_prd": o.get("tax_prd"),
                "pdf_url": o.get("pdf_url"),
                "source": "propublica",
            }
        )

    filings: list[dict[str, Any]] = []
    for r in irs:
        r_ein = re.sub(r"\D", "", r.get("EIN") or "")
        name = (r.get("TAXPAYER_NAME") or "").lower()
        if ein_digits and r_ein != ein_digits:
            continue
        if needle and needle not in name and (not ein_digits or r_ein != ein_digits):
            if not ein_digits:
                continue
        filings.append(
            {
                "ein": r.get("EIN"),
                "name": r.get("TAXPAYER_NAME"),
                "tax_period": r.get("TAX_PERIOD"),
                "return_type": r.get("RETURN_TYPE"),
                "object_id": r.get("OBJECT_ID"),
                "source_file": r.get("_source_file"),
            }
        )
        if len(filings) >= limit:
            break

    award_hits: list[dict[str, Any]] = []
    tokens = [t for t in re.split(r"\W+", needle) if len(t) >= 4] if needle else []
    for r in awards:
        recip = (r.get("RecipientName") or "").lower()
        # awards CSV has no EIN — name/token match only
        if ein_digits and not needle:
            continue
        if tokens:
            if not any(t in recip for t in tokens):
                continue
        elif needle and needle not in recip:
            continue
        cancel = (r.get("AwardCancellingNotes") or "").strip()
        status = (r.get("ProjectStatus") or "").strip()
        award_hits.append(
            {
                "recipient": r.get("RecipientName"),
                "agency": r.get("AgencyDept"),
                "title": r.get("ProjectTitle"),
                "fiscal_year": r.get("FiscalYear"),
                "award_amount": r.get("_award_amount"),
                "award_used": r.get("_award_used"),
                "status": status,
                "cancelling_notes": cancel or None,
                "grant_id": r.get("GrantID"),
                "source_file": r.get("_source_file"),
            }
        )
        if len(award_hits) >= limit:
            break

    return {
        "query": {"q": q, "ein": ein_digits or ein},
        "orgs": orgs[:limit],
        "irs_filings": filings[:limit],
        "ca_awards": award_hits[:limit],
        "counts": {
            "orgs": len(orgs),
            "irs_filings": len(filings),
            "ca_awards": len(award_hits),
        },
    }


def awards_for_name(name: str, *, limit: int = 25) -> list[dict[str, Any]]:
    needle = (name or "").strip().lower()
    if len(needle) < 4:
        return []
    # use first meaningful token(s)
    tokens = [t for t in re.split(r"\W+", needle) if len(t) >= 4][:3]
    if not tokens:
        return []
    hits: list[dict[str, Any]] = []
    for r in load_ca_grants():
        recip = (r.get("RecipientName") or "").lower()
        if any(t in recip for t in tokens):
            hits.append(r)
            if len(hits) >= limit:
                break
    return hits


def propublica_for_name(name: str) -> dict[str, Any] | None:
    needle = (name or "").strip().lower()
    if len(needle) < 4:
        return None
    tokens = [t for t in re.split(r"\W+", needle) if len(t) >= 4]
    best: dict[str, Any] | None = None
    best_score = 0
    for o in load_propublica_orgs():
        oname = (o.get("name") or "").lower()
        score = sum(1 for t in tokens if t in oname)
        if score > best_score:
            best_score = score
            best = o
    return best if best_score >= 2 else None


def corpus_summary() -> dict[str, Any]:
    fac = load_fac_findings()
    ca = load_ca_denied()
    gg = load_grants_gov_rejections()
    awards = load_ca_grants()
    irs = load_irs990_index()
    pp = load_propublica_orgs()

    fac_types: dict[str, int] = {}
    for r in fac:
        t = (r.get("type_requirement") or "unknown").strip()
        fac_types[t] = fac_types.get(t, 0) + 1

    ca_rates = {
        r["category"]: float(r.get("denial_rate") or 0)
        for r in ca
        if r.get("category") and r["category"] != "all"
    }
    buckets: dict[str, list[float]] = {}
    for r in ca:
        cat = r.get("category") or ""
        if cat in {"", "all"}:
            continue
        buckets.setdefault(cat, []).append(float(r.get("denial_rate") or 0))
    ca_avg = {k: sum(v) / len(v) for k, v in buckets.items()}

    gg_classes: dict[str, int] = {}
    for r in gg:
        c = r.get("rejection_class") or "other"
        gg_classes[c] = gg_classes.get(c, 0) + 1

    agencies: dict[str, int] = {}
    cancelled = 0
    nonprofit_awards = 0
    for r in awards:
        ag = (r.get("AgencyDept") or "unknown").strip() or "unknown"
        agencies[ag] = agencies.get(ag, 0) + 1
        if (r.get("AwardCancellingNotes") or "").strip():
            cancelled += 1
        if "nonprofit" in (r.get("RecipientType") or "").lower():
            nonprofit_awards += 1
    top_agencies = dict(sorted(agencies.items(), key=lambda kv: -kv[1])[:8])

    return_types: dict[str, int] = {}
    for r in irs:
        rt = r.get("RETURN_TYPE") or "unknown"
        return_types[rt] = return_types.get(rt, 0) + 1

    return {
        "fac_findings": len(fac),
        "fac_type_counts": fac_types,
        "ca_denied_rows": len(ca),
        "ca_category_avg_rates": ca_avg,
        "ca_category_rates_sample": ca_rates,
        "grants_gov_rejection_rows": len(gg),
        "grants_gov_class_counts": gg_classes,
        "ca_grants_awards": len(awards),
        "ca_grants_nonprofit_awards": nonprofit_awards,
        "ca_grants_with_cancel_notes": cancelled,
        "ca_grants_top_agencies": top_agencies,
        "irs990_index_rows": len(irs),
        "irs990_return_types": return_types,
        "propublica_orgs": len(pp),
        "limitations": {
            "fac": "Single Audit findings / questioned costs — proxy for documentation & allowability risk, not a denied-claim dataset",
            "ca_denied": "Aggregated Covered CA insurer denials by category — useful taxonomy priors for healthcare-adjacent nonprofits",
            "grants_gov": "Rejection Report is grantor-only; samples are schema-faithful synthetics (submission reject ≠ merit denial)",
            "ca_grants": "Post-award CA Grants Portal records — awards and usage, not reimbursement rejection outcomes",
            "irs990": "TEOS filing index only (truncated locally); use ProPublica for digitized financial fields",
            "propublica": "Digitized 990 subset — revenue/expenses/assets enrichment, not claim denials",
        },
        "paths": {
            "root": str(ROOT),
            "sources_md": str(ROOT / "SOURCES.md"),
        },
    }


# Map claim exception codes → corpus risk drivers
EXCEPTION_TO_DRIVERS: dict[str, list[str]] = {
    "missing_receipt": ["incorrect_submission", "Allowable Costs/Cost Principles", "Reporting"],
    "missing_invoice": ["incorrect_submission", "incorrect_billing", "Allowable Costs/Cost Principles"],
    "duplicate_expense": ["duplicate_claims", "Procurement and Suspension and Debarment"],
    "date_mismatch": ["Period of Performance", "incorrect_billing"],
    "budget_overrun": ["Allowable Costs/Cost Principles", "Reporting"],
    "missing_payroll": ["Allowable Costs/Cost Principles", "Eligibility"],
    "ineligible_participant": ["Eligibility", "ineligibility"],
    "unreconciled_gl": ["Reporting", "incorrect_submission"],
    "period_of_performance": ["Period of Performance"],
    "sam_uei_issue": ["ineligibility"],
    "schema_budget_mismatch": ["incorrect_submission", "incorrect_billing"],
}
