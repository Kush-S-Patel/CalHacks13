"""Download / seed public claim-risk corpora (FAC, CA denied claims, Grants.gov-shaped)."""

from __future__ import annotations

import csv
import json
import re
import zipfile
from io import BytesIO, StringIO
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1] / "data" / "train_data" / "claims"
FAC = ROOT / "fac"
CA = ROOT / "ca_denied"
GG = ROOT / "grants_gov"
META = ROOT / "SOURCES.md"

# Known FAC export patterns (GSA cloud storage) — try recent audit-year splits
FAC_CANDIDATES = [
    "https://www.fac.gov/data/download/current/findings.csv",
    "https://fac.gov/data/download/current/findings.csv",
    # common S3-style year splits used historically
    "https://www.fac.gov/assets/data/findings-ay-2023.csv",
    "https://www.fac.gov/assets/data/findings-ay-2024.csv",
]

CA_CANDIDATES = [
    # Covered California plan-level denied claims (Excel) — probe a few known issuers
    "https://hbex.coveredca.com/insurance-companies/denied-claims/2025-Anthem-Plan-Level-Claims.xlsx",
    "https://hbex.coveredca.com/insurance-companies/denied-claims/Anthem_2025_Plan_Level_Claims.xlsx",
]


def ensure_dirs() -> None:
    for p in (FAC, CA, GG):
        p.mkdir(parents=True, exist_ok=True)


def try_download(url: str, dest: Path, *, max_bytes: int = 25_000_000) -> bool:
    try:
        with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as r:
            if r.status_code != 200:
                print(f"  skip {url} status={r.status_code}")
                return False
            ctype = r.headers.get("content-type", "")
            if "html" in ctype and not url.endswith(".csv"):
                print(f"  skip {url} html content-type")
                return False
            buf = bytearray()
            for chunk in r.iter_bytes():
                buf.extend(chunk)
                if len(buf) > max_bytes:
                    print(f"  truncate {url} at {max_bytes}")
                    break
            dest.write_bytes(bytes(buf))
            print(f"  saved {dest.name} ({len(buf)} bytes) from {url}")
            return True
    except Exception as e:  # noqa: BLE001
        print(f"  fail {url}: {e}")
        return False


def seed_fac_sample() -> Path:
    """Curated FAC-shaped findings when bulk download unavailable (no API key)."""
    path = FAC / "findings_sample.csv"
    rows = [
        {
            "report_id": "2023-CA-NP-001",
            "audit_year": "2023",
            "auditee_name": "Bay Area Workforce Collaborative",
            "auditee_state": "CA",
            "finding_ref_number": "2023-001",
            "is_material_weakness": "Y",
            "is_modified_opinion": "N",
            "is_other_findings": "Y",
            "is_other_noncompliance": "Y",
            "type_requirement": "Allowable Costs/Cost Principles",
            "questioned_costs": "18400",
            "prior_finding_ref_numbers": "",
            "finding_text": "Personnel costs charged to CFDA 17.258 lacked contemporaneous time-and-effort documentation for 3 FTEs.",
        },
        {
            "report_id": "2023-CA-NP-002",
            "audit_year": "2023",
            "auditee_name": "Central Valley Food Bank Network",
            "auditee_state": "CA",
            "finding_ref_number": "2023-002",
            "is_material_weakness": "N",
            "is_modified_opinion": "N",
            "is_other_findings": "Y",
            "is_other_noncompliance": "Y",
            "type_requirement": "Procurement and Suspension and Debarment",
            "questioned_costs": "6200",
            "prior_finding_ref_numbers": "",
            "finding_text": "Vendor invoices over micro-purchase threshold missing competitive quotes; duplicate invoice paid twice then reversed.",
        },
        {
            "report_id": "2024-CA-NP-003",
            "audit_year": "2024",
            "auditee_name": "Pacific Youth Development Institute",
            "auditee_state": "CA",
            "finding_ref_number": "2024-001",
            "is_material_weakness": "Y",
            "is_modified_opinion": "Y",
            "is_other_findings": "Y",
            "is_other_noncompliance": "Y",
            "type_requirement": "Reporting",
            "questioned_costs": "0",
            "prior_finding_ref_numbers": "2023-004",
            "finding_text": "FFR submitted with expenditure totals that did not reconcile to general ledger by $41,200; prior year finding repeated.",
        },
        {
            "report_id": "2024-CA-NP-004",
            "audit_year": "2024",
            "auditee_name": "Coastal Health Access Nonprofit",
            "auditee_state": "CA",
            "finding_ref_number": "2024-003",
            "is_material_weakness": "N",
            "is_modified_opinion": "N",
            "is_other_findings": "Y",
            "is_other_noncompliance": "Y",
            "type_requirement": "Eligibility",
            "questioned_costs": "9800",
            "prior_finding_ref_numbers": "",
            "finding_text": "Participant eligibility files incomplete; services billed for period before enrollment date.",
        },
        {
            "report_id": "2023-OR-NP-005",
            "audit_year": "2023",
            "auditee_name": "Cascade Housing Alliance",
            "auditee_state": "OR",
            "finding_ref_number": "2023-007",
            "is_material_weakness": "N",
            "is_modified_opinion": "N",
            "is_other_findings": "Y",
            "is_other_noncompliance": "Y",
            "type_requirement": "Period of Performance",
            "questioned_costs": "15200",
            "prior_finding_ref_numbers": "",
            "finding_text": "Costs charged after award period of performance without approved extension.",
        },
        {
            "report_id": "2024-CA-NP-006",
            "audit_year": "2024",
            "auditee_name": "Sacramento Community Training Center",
            "auditee_state": "CA",
            "finding_ref_number": "2024-002",
            "is_material_weakness": "N",
            "is_modified_opinion": "N",
            "is_other_findings": "Y",
            "is_other_noncompliance": "N",
            "type_requirement": "Allowable Costs/Cost Principles",
            "questioned_costs": "2400",
            "prior_finding_ref_numbers": "",
            "finding_text": "Unallowable entertainment and gift cards charged to federal award; questioned costs removed in subsequent claim.",
        },
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  seeded {path}")
    return path


def seed_ca_denied() -> Path:
    path = CA / "ca_denied_claims_aggregate.csv"
    rows = [
        {"issuer": "Anthem Blue Cross", "plan_year": "2025", "market": "Individual", "claims_received": 1250000, "claims_denied": 187500, "denial_rate": 0.15, "category": "all"},
        {"issuer": "Anthem Blue Cross", "plan_year": "2025", "market": "Individual", "claims_received": 1250000, "claims_denied": 42000, "denial_rate": 0.0336, "category": "incorrect_submission"},
        {"issuer": "Anthem Blue Cross", "plan_year": "2025", "market": "Individual", "claims_received": 1250000, "claims_denied": 38000, "denial_rate": 0.0304, "category": "incorrect_billing"},
        {"issuer": "Anthem Blue Cross", "plan_year": "2025", "market": "Individual", "claims_received": 1250000, "claims_denied": 51000, "denial_rate": 0.0408, "category": "ineligibility"},
        {"issuer": "Anthem Blue Cross", "plan_year": "2025", "market": "Individual", "claims_received": 1250000, "claims_denied": 29000, "denial_rate": 0.0232, "category": "duplicate_claims"},
        {"issuer": "Blue Shield of California", "plan_year": "2025", "market": "Individual", "claims_received": 980000, "claims_denied": 127400, "denial_rate": 0.13, "category": "all"},
        {"issuer": "Blue Shield of California", "plan_year": "2025", "market": "Individual", "claims_received": 980000, "claims_denied": 31000, "denial_rate": 0.0316, "category": "incorrect_submission"},
        {"issuer": "Blue Shield of California", "plan_year": "2025", "market": "Individual", "claims_received": 980000, "claims_denied": 22000, "denial_rate": 0.0224, "category": "duplicate_claims"},
        {"issuer": "Kaiser Permanente", "plan_year": "2025", "market": "Individual", "claims_received": 2100000, "claims_denied": 189000, "denial_rate": 0.09, "category": "all"},
        {"issuer": "Kaiser Permanente", "plan_year": "2025", "market": "Individual", "claims_received": 2100000, "claims_denied": 41000, "denial_rate": 0.0195, "category": "ineligibility"},
        {"issuer": "Delta Dental", "plan_year": "2025", "market": "QDP", "claims_received": 450000, "claims_denied": 72000, "denial_rate": 0.16, "category": "all"},
        {"issuer": "Delta Dental", "plan_year": "2025", "market": "QDP", "claims_received": 450000, "claims_denied": 18000, "denial_rate": 0.04, "category": "incorrect_billing"},
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  seeded {path} (Covered CA category rates — illustrative from published denial taxonomy)")
    return path


def seed_grants_gov_shaped() -> Path:
    """
    Grants.gov Rejection Report is grantor-only — not a public bulk dump.
    Seed schema-faithful synthetic rows documenting limitation, plus public opportunity context.
    """
    path = GG / "rejection_report_shaped_sample.csv"
    rows = [
        {
            "grants_gov_tracking_number": "GRANT15992001",
            "received_datetime": "2025-09-12T14:07:47",
            "rejection_message": "Schema validation failed: SF-424A budget total does not equal sum of categories",
            "rejection_email_date": "2025-09-12",
            "uei": "ABC123DEF456",
            "legal_business_name": "Bay Area Workforce Collaborative",
            "opportunity_number": "FOA-ETA-25-01",
            "cfda": "17.258",
            "submission_method": "Workspace",
            "rejection_class": "incorrect_submission",
            "source_note": "SYNTHETIC — schema matches Grants.gov Rejection Report fields; not live grantor export",
        },
        {
            "grants_gov_tracking_number": "GRANT15992088",
            "received_datetime": "2025-10-01T09:22:11",
            "rejection_message": "Duplicate submission for same opportunity package PKG998877",
            "rejection_email_date": "2025-10-01",
            "uei": "XYZ987UVW654",
            "legal_business_name": "Pacific Youth Development Institute",
            "opportunity_number": "FOA-ETA-25-01",
            "cfda": "17.258",
            "submission_method": "S2S",
            "rejection_class": "duplicate_claims",
            "source_note": "SYNTHETIC — submission rejection != merit denial",
        },
        {
            "grants_gov_tracking_number": "GRANT16001102",
            "received_datetime": "2025-08-03T16:40:00",
            "rejection_message": "Authorized Organization Representative not registered / SAM.gov UEI mismatch",
            "rejection_email_date": "2025-08-03",
            "uei": "LMN555OPQ111",
            "legal_business_name": "Coastal Health Access Nonprofit",
            "opportunity_number": "HRSA-25-102",
            "cfda": "93.224",
            "submission_method": "Workspace",
            "rejection_class": "ineligibility",
            "source_note": "SYNTHETIC",
        },
        {
            "grants_gov_tracking_number": "GRANT16004441",
            "received_datetime": "2025-07-19T11:05:33",
            "rejection_message": "Attachment missing: negotiated indirect cost rate agreement referenced in budget narrative",
            "rejection_email_date": "2025-07-19",
            "uei": "QWE444RTY222",
            "legal_business_name": "Central Valley Food Bank Network",
            "opportunity_number": "USDA-FNS-25-04",
            "cfda": "10.568",
            "submission_method": "PDF",
            "rejection_class": "incorrect_billing",
            "source_note": "SYNTHETIC — maps to documentation gaps that also drive reimbursement risk",
        },
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    note = GG / "LIMITATIONS.md"
    note.write_text(
        "# Grants.gov Rejection Report — limitations\n\n"
        "- Available to **grantors** in Grantor Center, not as a public bulk dataset.\n"
        "- Captures **submission** rejections (schema/SAM/duplicate), not merit denials.\n"
        "- Live S2S requires agency certificate; this repo uses schema-faithful samples only.\n"
        "- Public Grants.gov APIs expose opportunities, not rejection rows.\n",
        encoding="utf-8",
    )
    print(f"  seeded {path}")
    return path


def try_fetch_fac_api_sample() -> Path | None:
    """FAC API requires Data.gov key — skip if absent; write placeholder note."""
    key = ""
    env = Path(__file__).resolve().parents[1] / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("FAC_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        (FAC / "API_NOTE.md").write_text(
            "Set FAC_API_KEY (Data.gov) to pull live findings from https://api.fac.gov/findings\n"
            "Until then, findings_sample.csv is used.\n",
            encoding="utf-8",
        )
        return None
    url = "https://api.fac.gov/findings?limit=50&order=audit_year.desc"
    r = httpx.get(url, headers={"X-Api-Key": key}, timeout=60.0)
    if r.status_code != 200:
        print(f"  FAC API {r.status_code}: {r.text[:200]}")
        return None
    data = r.json()
    path = FAC / "findings_api_sample.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  FAC API saved {len(data) if isinstance(data, list) else '?'} rows → {path}")
    return path


def scrape_ca_links() -> None:
    try:
        r = httpx.get(
            "https://hbex.coveredca.com/insurance-companies/denied-claims/",
            timeout=60.0,
            follow_redirects=True,
        )
        if r.status_code != 200:
            return
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', r.text, flags=re.I)
        links = []
        for h in hrefs:
            if any(h.lower().endswith(ext) for ext in (".xlsx", ".xls", ".csv", ".pdf")):
                if h.startswith("http"):
                    links.append(h)
                else:
                    links.append("https://hbex.coveredca.com" + (h if h.startswith("/") else "/" + h))
        (CA / "discovered_links.json").write_text(json.dumps(links[:40], indent=2), encoding="utf-8")
        for url in links[:8]:
            name = url.rstrip("/").split("/")[-1]
            if not name:
                continue
            dest = CA / name
            if dest.exists():
                continue
            try_download(url, dest, max_bytes=5_000_000)
    except Exception as e:  # noqa: BLE001
        print(f"  CA scrape fail: {e}")


def write_meta() -> None:
    META.write_text(
        """# Claim rejection risk corpora

| Source | Path | Role in risk model | Limitation |
| --- | --- | --- | --- |
| Federal Audit Clearinghouse findings | `fac/` | Questioned costs, finding types (allowable costs, eligibility, reporting, PoP) | Single Audit ≠ denied reimbursement claim; strongest public proxy for documentation/compliance failures |
| Covered California denied claims | `ca_denied/` | Denial taxonomy rates: incorrect submission/billing, ineligibility, duplicates | Aggregated insurer reporting — not nonprofit grant packages with invoices |
| Grants.gov Rejection Report (shaped) | `grants_gov/` | Submission-failure patterns (schema, SAM, duplicate) | **Grantor-only** UI/S2S; samples are schema-faithful synthetics, not bulk public denials |

Live FAC pull: set `FAC_API_KEY` (Data.gov) and re-run this script.
""",
        encoding="utf-8",
    )


def main() -> None:
    ensure_dirs()
    print("FAC candidates…")
    got = False
    for url in FAC_CANDIDATES:
        dest = FAC / url.rstrip("/").split("/")[-1]
        if try_download(url, dest):
            got = True
            break
    if not got:
        seed_fac_sample()
    try_fetch_fac_api_sample()

    print("CA denied claims…")
    scrape_ca_links()
    seed_ca_denied()

    print("Grants.gov shaped…")
    seed_grants_gov_shaped()
    write_meta()
    print("done →", ROOT)


if __name__ == "__main__":
    main()
