# SwarmCFO Claims

**One corner done deep:** nonprofit grant reimbursement packages that **learn from a manager’s no**, improve the next case, and **prove** it in an append-only audit.

Not a scripted happy path. Not ten shallow workflows. Not a bakery clone of the Hyphenate workshop examples.

## The Hyphenate loop (primary demo)

1. **Claims Agent** prepares revision 1  
2. Detects **four** critical exceptions  
3. **Asks** about the ambiguous **$860** catering charge  
4. **Finance Manager:** “No—staff celebration. Exclude it.”  
5. Correction → **revision 2**  
6. Correction saved as a **precedent**  
7. System proposes a **policy** for future staff celebrations  
8. Similar **next-month** expense is **auto-held** by that policy  
9. Claims Agent tries to approve → **DENIED** (role limits in code)  
10. **Finance Manager** approves the package  
11. **Audit** shows question, answer, revision diff, policy version, denied attempt, final approval  

### Objective results

| Metric | Result |
| --- | ---: |
| Excluded / moved out of claim | **$8,160** |
| Receipt attached | **$124** |
| Eligible reimbursement | **$28,135** |
| Critical exceptions | **4 → 0** |
| Unauthorized approvals | **0** |
| Every transition | audited |

## Quick start

```bash
npm install
npm run agents   # :8765
npm run dev      # :3000
```

```bash
curl -X POST http://127.0.0.1:8765/v1/claims/demo
```

UI: open `/` → **Run Claims learning loop**, or `/suite/claims`.

## What is governed (not labels)

| Actor | Role | May | May not |
| --- | --- | --- | --- |
| `agent-claims` | `ai_claims` | prepare, ask, hold, propose policy | **approve**, post |
| `human-finance-manager` | `human_finance_manager` | answer, approve claim + policy, create precedent | post to funder |
| `gateway` | gateway | post SoR | — |

Claims **never submit** to the funder and **never alter** the ledger.

## Risk priors (supporting)

FAC findings · Covered CA denial taxonomy · Grants.gov-shaped samples · CA Grants Portal awards · IRS 990 index · ProPublica 990 financials  

```bash
python scripts/fetch_claims_sources.py
python scripts/fetch_nonprofit_financials.py
```

## Repo layout

```
agents/claims/learning_loop.py   Hyphenate sequence + objective results
agents/claims/pipeline.py        Match / exceptions / validation
agents/claims/risk.py            Deterministic rejection-risk score
agents/sow/                      Roles, transitions, audit diffs, policies
apps/web/                        Claims-first UI + learning viz
```

## Secondary surfaces

Mission Margin (`/suite/jobs`), ERP vault, graphs, Nessie/NetSuite — available, **not** the lead pitch.
