# SwarmCFO — Mission Margin Controller

**Sell a financial result, not an agent architecture:** every client deliverable runs as a budgeted multi-agent mission with hard tool-spend limits, audited denials, and a job-cost ledger (quote vs actual cost vs margin).

The Hyphenate **system of work** (World · Time · Team · Limits) is the control plane. Maya’s Bakery remains the messy-corner demo that proves roles, gateway posts, and audit. The product wedge for agencies is **Jobs** (`/suite/jobs`): fixed-price work that stays profitable.

> Harnesses made agents capable. SwarmCFO makes autonomous jobs **accountable**.

## Why this wins the Hyphenate track

| Judge ask | SwarmCFO |
| --- | --- |
| **Is it real enough?** | Maya’s Bakery messy corner: short wires, duplicate AP, late AR, spend holds |
| **Would you hire it?** | Roles + `can()` in code; gateway-only posts; owner Approve |
| **Something new?** | Self-learning policies from history; corrections → precedents → pol-014 |
| **Wow moment?** | Runway 11→~20, $4.2k fraud BLOCKED, $1.4k HELD → one-tap Approve on every screen |

**Not a chatbot over a spreadsheet.** Tools are CRUD on work items. Memory is policies + precedents (not the context window). Limits are enforced in code — denied attempts are audited.

## The Hyphenate blueprint (mapped)

```
SYSTEMS OF RECORD          GATEWAY              SYSTEM OF WORK (this repo)
Bank / AP / CRM / Stripe ──► one door ──► work items · policies · precedents · audit
                              │
                         agents + Maya share the same queue
```

| Build | What we shipped |
| --- | --- |
| **1 Environment** | `sow/sync.py` — raw ledger → golden records, stable ids, cursors |
| **2 Team** | `sow/roles.py` — actors, SoD (proposer ≠ approver), gateway-only `post` |
| **3 Harness** | `sow/transitions.py` — NEW→PROPOSED→…→POSTED; tools = transitions |
| **4 Traceability** | `sow/audit.py` — append-only diffs; `/v1/audit/{subject}` = “why?” |
| **Self-learning** | `sow/learn.py` — pol-001 short wire, pol-002 duplicate, pol-003 autonomy |
| **Self-improving** | `sow/improve.py` — rejections & corrections → precedents → pol-014 |

## Roles (few, done deep)

| Actor | Corner |
| --- | --- |
| **Risk** | Cash match (short wires), AP duplicate block |
| **Procurement** | Supplier spike → counter-offer |
| **Collections** | Late AR chase + early-pay |
| **Cashier** | ≤$1k autonomy; above → HELD |
| **CFO** | Arbitrate disagreements; defer spend; own runway |
| **Maya (owner)** | Answer / Approve / Reject |
| **Gateway** | Sole writer to systems of record |

## Quick start

```bash
cp .env.example .env
npm install
pip install -r agents/requirements.txt

# Terminal A — system of work API (port 8765 — 8000 is often taken)
npm run agents
# expect http://127.0.0.1:8765/health → "swarmcfo" fields

# Terminal B — product UI
npm run dev
# Big screen http://localhost:3000  ·  Graphs /graphs  ·  Phone /phone
```

If you see `{"detail":"Not Found"}`, something else is bound to that port — confirm `GET /` returns `"service":"swarmcfo"`.

**Offline / Wi-Fi dead (answer key):**

```bash
npm run sow          # python -m sow.scenario → poc/last_sow_run.json · score 100
```

## Product surfaces

- **Mission Margin Controller** (`/suite/jobs`, `POST /v1/missions/demo`) — quote $250 / max tool spend $8; research→extract→verify under `BudgetController`; overspend **DENIED + audited**; deliverable + job ledger + margin  
- **ERP Suite** (`/suite`) — enterprise **Summary**, **Upload** analyzer, **Documents** vault, **Graphs**, **Work**  
- **Document intake** — FinDoc OCR + FinCriticalED + [DocILE](https://github.com/rossumai/docile) → vault / per-business knowledge  
- **Capital One Nessie** — live bank-sim rail; UI shows the Nessie mark  
- **Claude agents** — `POST /v1/agents/{risk|cfo|…}/run` → audited SoW transitions  
- **NetSuite-shaped SoR** — gateway fan-out (`GET /v1/erp/netsuite`)  

### Future domain: Claims (not this slice)

Nonprofit grant **reimbursement packages** (award rules → match ledger↔evidence → compliance exceptions → draft claim) remain Plan B if agency interviews show weak job-margin pain. That needs a new accounting/award domain layer — not a retrofit of market tools.


- **Runway** — the one number Maya cares about  
- **Company graphs** — supply chain / context / relationships with **exact USD**; **fraud in red**  
- **Work queue** — PROPOSED / NEEDS_INFO / HELD / BLOCKED / POSTED  
- **Phone** — QR join · Approve · run demo  

## Repo layout

```
agents/missions/  Mission Margin Controller (budget, metered tools, job ledger)
agents/sow/       System of work engine (control plane)
agents/main.py    FastAPI — world, missions, erp, nessie, agents
apps/web/         Next.js world + ERP suite + Jobs
spacetime/        Multiplayer shared state
data/seed/        Messy bakery ledger + answer key
poc/              Deterministic sims + last_sow_run.json
```

## Demo (3 min) — geared to Hyphenate

1. **Pain** — runway ticking at 11 days  
2. **Onboarding** — show pol-001 learned from 7 historical short wires  
3. **Chaos** — short wire asks Maya; duplicate BLOCKED (agent approve DENIED on screen); spike disagreement → CFO arbitrate; AR chase; $1.4k HELD  
4. **Approve** — Maya taps; gateway posts; every screen updates  
5. **Score** — Hyphenate 100 · “This is the team a one-person company would hire”  
6. **Close** — query `/v1/audit/inv-dup-incoming` — why? is one query  

Script detail: [`DEMO.md`](./DEMO.md)

## Outcome-shaped pitch (pricing story)

SaaS sells seats. Hyphenate sells **work**. SwarmCFO proves outcomes: blocked fraud dollars, posted matches, approved holds — each an audited work item. That’s how you bill per result.

## Sponsor fit

- **Hyphenate** — Autonomous Systems for Finance (primary)  
- **Creao** — Best One-Person Company  
- **SpacetimeDB** — shared live world for agents + humans  
- **CRS / Anthropic** — financial agents with tools, not chat theatre  

## License

MIT — CalHacks 13.0
