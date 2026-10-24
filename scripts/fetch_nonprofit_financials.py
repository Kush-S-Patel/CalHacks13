"""
Collect nonprofit financials + award/rejection-adjacent corpora:

  - IRS Form 990 TEOS index (CSV) — filing inventory; full XML bulk is huge
  - ProPublica Nonprofit Explorer API — searchable 990 financials (no key)
  - Federal Audit Clearinghouse — reuse claims/fac samples (+ optional API key)
  - California Grants Portal award CSVs — awardee / funding relationships

Writes under data/train_data/claims/{irs990,propublica,ca_grants,fac}/
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1] / "data" / "train_data" / "claims"
IRS = ROOT / "irs990"
PP = ROOT / "propublica"
CAG = ROOT / "ca_grants"
FAC = ROOT / "fac"

CA_AWARDS_URL = (
    "https://data.ca.gov/dataset/14aca9b5-d384-43eb-ba8e-81fc94aea432/"
    "resource/97bbaf09-c935-4897-9529-b8cc56b080a1/download/"
    "grant-awards-fiscal-year-2024-2025.csv"
)
CA_AWARDS_2324 = (
    "https://data.ca.gov/dataset/572d06aa-4f1f-44ad-80a4-167bec020881/"
    "resource/018f3523-652d-4197-a4a8-a055bfd1544f/download/"
    "grant-awards-fiscal-year-2023-2024.csv"
)

IRS_INDEX_2024 = "https://apps.irs.gov/pub/epostcard/990/xml/2024/index_2024.csv"
IRS_INDEX_2025 = "https://apps.irs.gov/pub/epostcard/990/xml/2025/index_2025.csv"

PP_SEARCH = "https://projects.propublica.org/nonprofits/api/v2/search.json"
PP_ORG = "https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json"

# Demo / seed orgs to hydrate from ProPublica (real CA nonprofits when searchable)
SEED_QUERIES = [
    ("workforce california", {"state[id]": "CA", "ntee[id]": "5"}),
    ("food bank california", {"state[id]": "CA", "ntee[id]": "5"}),
    ("youth development oakland", {"state[id]": "CA"}),
    ("community health california", {"state[id]": "CA", "ntee[id]": "4"}),
]


def ensure() -> None:
    for p in (IRS, PP, CAG, FAC):
        p.mkdir(parents=True, exist_ok=True)


def download(url: str, dest: Path, *, max_bytes: int = 40_000_000, max_rows: int | None = None) -> bool:
    try:
        with httpx.stream("GET", url, timeout=180.0, follow_redirects=True) as r:
            if r.status_code != 200:
                print(f"  skip {url} → {r.status_code}")
                return False
            ctype = (r.headers.get("content-type") or "").lower()
            if "html" in ctype and "csv" not in url.lower():
                print(f"  skip html {url}")
                return False
            if max_rows and url.lower().endswith(".csv"):
                # stream-truncate CSV to first N data rows
                text_chunks: list[str] = []
                size = 0
                for chunk in r.iter_text():
                    text_chunks.append(chunk)
                    size += len(chunk.encode("utf-8", errors="ignore"))
                    if size > max_bytes:
                        break
                text = "".join(text_chunks)
                lines = text.splitlines()
                keep = lines[: max_rows + 1]  # header + rows
                dest.write_text("\n".join(keep) + "\n", encoding="utf-8")
                print(f"  saved {dest.name} ({len(keep)-1} rows, truncated) from {url}")
                return True
            buf = bytearray()
            for chunk in r.iter_bytes():
                buf.extend(chunk)
                if len(buf) > max_bytes:
                    print(f"  truncate at {max_bytes} {url}")
                    break
            dest.write_bytes(bytes(buf))
            print(f"  saved {dest.name} ({len(buf)} bytes)")
            return True
    except Exception as e:  # noqa: BLE001
        print(f"  fail {url}: {e}")
        return False


def fetch_ca_grants() -> None:
    print("California Grants Portal awards…")
    ok = download(CA_AWARDS_URL, CAG / "grant-awards-fy-2024-2025.csv", max_rows=5000)
    if not ok:
        download(CA_AWARDS_2324, CAG / "grant-awards-fy-2023-2024.csv", max_rows=5000)
    # small summary JSON
    for path in CAG.glob("grant-awards*.csv"):
        with path.open(encoding="utf-8", newline="", errors="replace") as f:
            rows = list(csv.DictReader(f))
        (CAG / f"{path.stem}_summary.json").write_text(
            json.dumps(
                {
                    "file": path.name,
                    "rows": len(rows),
                    "columns": list(rows[0].keys()) if rows else [],
                    "sample": rows[:3],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"  summary {path.name}: {len(rows)} rows, cols={list(rows[0].keys())[:8] if rows else []}")


def fetch_irs_index() -> None:
    print("IRS Form 990 TEOS index…")
    ok = download(IRS_INDEX_2024, IRS / "index_2024.csv", max_bytes=15_000_000, max_rows=8000)
    if not ok:
        download(IRS_INDEX_2025, IRS / "index_2025.csv", max_bytes=15_000_000, max_rows=8000)
    (IRS / "NOTE.md").write_text(
        "# IRS Form 990 bulk data\n\n"
        "- Full TEOS XML monthly ZIPs are multi‑GB — we store the **index CSV** for EIN/object_id lookup.\n"
        "- XML downloads: https://www.irs.gov/charities-non-profits/form-990-series-downloads\n"
        "- Pair with ProPublica API for digitized revenue/expense fields without parsing XML.\n",
        encoding="utf-8",
    )


def fetch_propublica() -> None:
    print("ProPublica Nonprofit Explorer…")
    client = httpx.Client(timeout=60.0, follow_redirects=True, headers={"User-Agent": "SwarmCFOClaims/0.1"})
    orgs: list[dict] = []
    for q, extra in SEED_QUERIES:
        params = {"q": q, **extra}
        try:
            r = client.get(PP_SEARCH, params=params)
            if r.status_code != 200:
                print(f"  search fail {q}: {r.status_code}")
                continue
            data = r.json()
            for o in (data.get("organizations") or [])[:5]:
                orgs.append(o)
                ein = o.get("ein") or o.get("id")
                if not ein:
                    continue
                detail_path = PP / f"org_{ein}.json"
                if detail_path.exists():
                    continue
                dr = client.get(PP_ORG.format(ein=ein))
                if dr.status_code == 200:
                    detail_path.write_text(json.dumps(dr.json(), indent=2), encoding="utf-8")
                    print(f"  org {ein} {o.get('name')}")
        except Exception as e:  # noqa: BLE001
            print(f"  PP error {q}: {e}")

    # Dedupe search hits
    seen = set()
    uniq = []
    for o in orgs:
        ein = str(o.get("ein") or o.get("id") or "")
        if ein and ein not in seen:
            seen.add(ein)
            uniq.append(o)
    (PP / "search_hits.json").write_text(json.dumps(uniq, indent=2), encoding="utf-8")
    print(f"  {len(uniq)} unique search hits; {len(list(PP.glob('org_*.json')))} org detail files")

    # Flatten a compact financials CSV from org details
    flat_rows = []
    for path in sorted(PP.glob("org_*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        org = raw.get("organization") or raw
        filings = raw.get("filings_with_data") or []
        latest = filings[0] if filings else {}
        flat_rows.append(
            {
                "ein": org.get("ein") or path.stem.replace("org_", ""),
                "name": org.get("name") or "",
                "city": org.get("city") or "",
                "state": org.get("state") or "",
                "ntee_code": org.get("ntee_code") or "",
                "revenue": latest.get("totrevenue") or latest.get("total_revenue") or "",
                "expenses": latest.get("totfuncexpns") or latest.get("total_functional_expenses") or "",
                "assets": latest.get("totassetsend") or latest.get("total_assets") or "",
                "tax_prd": latest.get("tax_prd") or latest.get("tax_period") or "",
                "formtype": latest.get("formtype") or latest.get("form_type") or "",
                "pdf_url": latest.get("pdf_url") or "",
            }
        )
    if flat_rows:
        with (PP / "org_financials.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(flat_rows[0].keys()))
            w.writeheader()
            w.writerows(flat_rows)
        print(f"  wrote org_financials.csv ({len(flat_rows)} orgs)")


def write_sources() -> None:
    path = ROOT / "SOURCES.md"
    prev = path.read_text(encoding="utf-8") if path.exists() else ""
    extra = """
## Nonprofit financials & awards (added)

| Source | Path | What we use | Limitation |
| --- | --- | --- | --- |
| IRS Form 990 TEOS index | `irs990/` | EIN / object_id inventory for filings | Full XML ZIPs are multi‑GB; index + ProPublica used for financial fields |
| ProPublica Nonprofit Explorer API | `propublica/` | Revenue, expenses, assets, NTEE, filings | Digitized subset of 990s; not every schedule |
| California Grants Portal awards | `ca_grants/` | Award–awardee relationships, amounts, agencies | Post-award data lags; awards ≠ reimbursement outcomes |
| Federal Audit Clearinghouse | `fac/` | Compliance findings / questioned costs | Still the best public **failure-mode** proxy |

Refresh: `python scripts/fetch_nonprofit_financials.py`
"""
    if "Nonprofit financials & awards" not in prev:
        path.write_text(prev.rstrip() + "\n" + extra, encoding="utf-8")
    print("  updated SOURCES.md")


def main() -> None:
    ensure()
    fetch_ca_grants()
    fetch_irs_index()
    fetch_propublica()
    write_sources()
    print("done →", ROOT)


if __name__ == "__main__":
    main()
