# SwarmCFO

**Autonomous finance for a one-person company — built as a Hyphenate *system of work*.**

Maya’s Bakery: $18,400 cash, $1,650/day burn, **11 days runway**. She is CEO, baker, and the entire finance department. SwarmCFO is the finance team she would hire — agents that **do the work**, ask when judgment is needed, and prove every call.

> Harnesses made agents capable. This puts them inside a company: **World · Time · Team · Limits.**

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

- **ERP Suite** (`/suite`) — enterprise **Summary**, **Upload** analyzer, **Documents** vault, **Graphs**, **Work**  
- **Document intake** — FinDoc OCR ([financial-documents](https://huggingface.co/datasets/daitavan/financial-documents)) + FinCriticalED ([dataset](https://huggingface.co/datasets/TheFinAI/FinCriticalED)) + [DocILE](https://github.com/rossumai/docile) invoices from `data/train_data` → classify → extract → vault
- **Per-business knowledge** — DocILE KILE/LIR fields expand each issuing vendor into customers, supply-chain parties, SKUs, and relationship strength (`/suite/businesses`, `POST /v1/erp/intake/docile`). Download: `.\scripts\download_docile.ps1 $env:DOCILE_TOKEN`  
- **Spreadsheet analyzer** — CSV/XLSX (+ scanned text); maps CoA / revenue / AP / AR / supply chain into the vault  
- **Digital vault** — stores uploads under `data/erp_vault/`; adjacent to NetSuite / QBO / Stripe / bank  
- **Capital One Nessie** — live bank-sim rail (`NESSIE_API_KEY` → `https://api.nessieisreal.com`); demo posts deposits/withdrawals; UI shows the Nessie mark  

- **Runway** — the one number Maya cares about  
- **Company graphs** — supply chain / context / relationships with **exact USD**; **fraud in red**  
- **Work queue** — PROPOSED / NEEDS_INFO / HELD / BLOCKED / POSTED  
- **Phone** — QR join · Approve · run demo  

## Repo layout

```
agents/sow/       System of work engine (the product core)
agents/main.py    FastAPI — world, audit, approve, demo, score
apps/web/         Next.js world + phone
spacetime/        Multiplayer shared state (work_item, policy, audit_event)
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
