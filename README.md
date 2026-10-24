# SwarmCFO Claims

**Outcome sold:** a complete, supported **nonprofit grant reimbursement package** ready for a finance manager to approve — with an explicit **rejection-risk score** grounded in public compliance and denial corpora.

Not a grant-management ERP. Not a chatbot over a spreadsheet. The final mile: connect ledger transactions to the evidence and rules a reimbursement submission actually needs, then predict where the package is still likely to fail.

> Customers: outsourced nonprofit bookkeeping / fractional-CFO firms that repeat the same claim assembly across many grantees.

## Why this problem is real

- California Little Hoover Commission (2025–26): majority of nonprofits report burdensome reporting; delayed reimbursements are systemic.
- Federal award rules (2 CFR 200): track expenditures vs budget, retain support, determine allowability.
- Automation can **prepare a more complete claim**; it cannot force an agency to pay faster.

## Controlled workflow

1. **Award analyst** — agreement + budget → structured rulebook (human-approvable)
2. **Transaction matcher** — GL ↔ receipt/invoice/payroll with confidence
3. **Compliance reviewer** — missing docs, duplicates, date/PoP issues, budget gaps (evidence-backed exceptions)
4. **Deterministic validation** — totals, recon, budget caps in **code**
5. **Claim preparer + risk scorer** — schedules, evidence index, unresolved exceptions, **rejection risk 0–100**

Mission constraint example: *Prepare Award A for September. Reconcile expenses, flag missing support, draft the claim. Do not submit. Do not alter the ledger.*

## Rejection-risk data priors

| Source | Use | Limitation (honored in product copy) |
| --- | --- | --- |
| **Federal Audit Clearinghouse** findings | Finding types, material weakness, questioned costs → allowability / reporting / PoP / eligibility priors | Single Audit ≠ denied reimbursement dataset; best public proxy for documentation failures |
| **Covered CA denied claims** | Category rates: incorrect submission, incorrect billing, ineligibility, duplicates | Aggregated insurer reporting — taxonomy priors for healthcare-adjacent nonprofits, not invoice-level grant cases |
| **Grants.gov Rejection Report** (shaped samples) | Submission failures (schema, SAM, duplicate) | **Grantor-only**; not public bulk; submission reject ≠ merit denial |
| **California Grants Portal awards** | Award–awardee relationships, cancel notes, drawdown context | Post-award records; awards ≠ reimbursement rejection outcomes |
| **IRS Form 990 TEOS index** | EIN / filing inventory for nonprofit identity | Full XML bulk is multi‑GB; index only (truncated locally) |
| **ProPublica Nonprofit Explorer** | Digitized 990 revenue / expenses / assets enrichment | Not claim denials; digitized subset of filings |

Corpora live under [`data/train_data/claims/`](data/train_data/claims/) — refresh with:

```bash
python scripts/fetch_claims_sources.py
python scripts/fetch_nonprofit_financials.py
# optional: FAC_API_KEY=<Data.gov key> for live api.fac.gov findings
```

## Quick start

```bash
npm install
npm run agents   # :8765
npm run dev      # :3000 → /suite/claims
```

```bash
curl -X POST http://127.0.0.1:8765/v1/claims/demo
curl http://127.0.0.1:8765/v1/claims/corpus
curl "http://127.0.0.1:8765/v1/claims/nonprofit?q=food%20bank"
```

## Product surfaces

- **Claims** (`/suite/claims`, `POST /v1/claims/demo`) — primary demo
- **Jobs** (`/suite/jobs`) — Mission Margin Controller (secondary: budgeted AI-agency jobs)
- **ERP Suite** — vault, DocILE enterprises, NetSuite-shaped SoR, Nessie bank rail
- **World** — Hyphenate system-of-work control plane (roles, gateway, audit)

## Repo layout

```
agents/claims/     Reimbursement pipeline + risk scorer
agents/missions/   Mission Margin (secondary)
agents/sow/        System of work engine
agents/main.py     FastAPI
data/train_data/claims/   FAC / CA denied / Grants.gov / CA awards / IRS 990 / ProPublica
apps/web/          Next.js suite
```

## Demo (3 min)

1. **Pain** — monthly workforce-grant reimbursement; missing receipts, duplicate invoice, celebration lunch, wage after period
2. **Run** — Prepare reimbursement claim
3. **Show** — matches, exceptions, GL recon, risk band + corpus drivers
4. **Outcome** — package ready for manager approval; system never submits
5. **Optional** — full demo also runs bakery SoW for control-plane proof

## Success metrics (product)

Preparation hours/claim · % transactions matched to support · discrepancies caught pre-submit · % submissions needing corrections · calibration of risk score vs later outcomes (when labeled data exists)
