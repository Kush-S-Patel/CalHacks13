# Claim rejection risk corpora

| Source | Path | Role in risk model | Limitation |
| --- | --- | --- | --- |
| Federal Audit Clearinghouse findings | `fac/` | Questioned costs, finding types (allowable costs, eligibility, reporting, PoP) | Single Audit ≠ denied reimbursement claim; strongest public proxy for documentation/compliance failures |
| Covered California denied claims | `ca_denied/` | Denial taxonomy rates: incorrect submission/billing, ineligibility, duplicates | Aggregated insurer reporting — not nonprofit grant packages with invoices |
| Grants.gov Rejection Report (shaped) | `grants_gov/` | Submission-failure patterns (schema, SAM, duplicate) | **Grantor-only** UI/S2S; samples are schema-faithful synthetics, not bulk public denials |

Live FAC pull: set `FAC_API_KEY` (Data.gov) and re-run this script.

## Nonprofit financials & awards (added)

| Source | Path | What we use | Limitation |
| --- | --- | --- | --- |
| IRS Form 990 TEOS index | `irs990/` | EIN / object_id inventory for filings | Full XML ZIPs are multi‑GB; index + ProPublica used for financial fields |
| ProPublica Nonprofit Explorer API | `propublica/` | Revenue, expenses, assets, NTEE, filings | Digitized subset of 990s; not every schedule |
| California Grants Portal awards | `ca_grants/` | Award–awardee relationships, amounts, agencies | Post-award data lags; awards ≠ reimbursement outcomes |
| Federal Audit Clearinghouse | `fac/` | Compliance findings / questioned costs | Still the best public **failure-mode** proxy |

Refresh: `python scripts/fetch_nonprofit_financials.py`
