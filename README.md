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

# Terminal A — system of work API
cd agents && python -m uvicorn main:app --reload --port 8000

# Terminal B — product UI
npm run dev
# Big screen http://localhost:3000  ·  Phone http://localhost:3000/phone
```

**Offline / Wi-Fi dead (answer key):**

```bash
npm run sow          # python -m sow.scenario → poc/last_sow_run.json · score 100
```

## Product surfaces

- **Runway** — the one number Maya cares about  
- **Company graphs** (`/` + `/graphs`) — full supply chain, context graph, relationship graph with **exact USD** on every edge; **fraud in red**, holds in amber  
- **Work queue** — state machine (PROPOSED / NEEDS_INFO / HELD / BLOCKED / POSTED)  
- **Learned policies** — pol-001…014 drafted from history  
- **Audit trail** — every transition + denials  
- **Hyphenate score** — live scorecard against judging criteria  
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
