# SwarmCFO

**A one-person company with a full finance team.**

Maya runs a bakery alone. She has $18,400 in the bank, burns $1,650/day, and has **11 days of cash runway** — and she is simultaneously the CEO, the baker, and the entire finance department.

SwarmCFO gives her five autonomous agents that share one live financial world (SpacetimeDB) with her phone, a partner’s laptop, and the demo big screen. Every agent decision is a real, auditable action — block, counter, chase, pay, hold — not a chat transcript.

## The five agents

| Agent | Job | Autonomy |
| --- | --- | --- |
| **CFO** | Owns the runway number; arbitrates disagreements; recomputes cash after every event | Governance |
| **Risk / Fraud** | Duplicate detection, vendor legitimacy, anomalous amounts | Block / flag |
| **Procurement** | Watches supplier prices; drafts counter-offers | Counter / recommend |
| **Collections** | Escalating, tone-aware chase + early-pay incentives | Chase AR |
| **Cashier** | Executes payments ≤ $1,000; holds anything above for one-tap approval | Pay / hold |

Owner UI is intentionally one number (**runway**) and one button (**Approve**). Complexity lives under the hood.

## Demo (3 minutes)

1. **0:00–0:20** — Pain + runway counter ticking  
2. **0:20–0:50** — Judge injects chaos (QR join from phones)  
3. **0:50–1:40** — Tool calls, not chat: BLOCKED invoice, SENT counter-offer, visible agent disagreement  
4. **1:40–2:20** — $1,400 hold → owner tap → every screen updates  
5. **2:20–3:00** — Close: “2,000 students here will start something alone. None can hire a finance team. This is the team.”

Worked chaos scenario (also in `poc/swarmcfo_sim.py`):

- Supplier raises prices 40% → Procurement counters (~$2,728/mo saved)  
- Duplicate $4,200 invoice → Risk blocks it  
- Customer 12 days late on $9,200 → Collections accelerates  
- CFO defers $3,800 non-critical spend → runway **11 → 20 days**  
- $1,400 supplier deposit sits in **WAITING** until Maya taps Approve  

## Architecture

```
apps/web          Next.js world-view + phone controller (QR join)
spacetime/        SpacetimeDB tables + reducers (shared live world)
agents/           5 Claude agents: system prompt + tools + $ autonomy limit
poc/              Deterministic offline sim (Wi-Fi/API fallback)
data/seed         Frozen bakery ledger (30 invoices, 4 suppliers, 90 days cash)
```

**Invariant:** Claude decides; SpacetimeDB reducers execute. That separation is the anti-“chat theatre” story.

```
Judge / Owner phone ──► Next.js ──► SpacetimeDB reducers
                              ▲            │
                              │            ▼
                         subscriptions   agent service (Anthropic)
                              │            │
                              └────────────┘  live multiplayer world
```

### SpacetimeDB tables

`cash` · `invoices` · `suppliers` · `orders` · `agent_actions` · `approvals` · `runway`

### Reducers

`inject_chaos` · `block_invoice` · `counter_offer` · `chase_ar` · `pay` · `hold` · `approve` · `recompute_runway`

## Repo layout

```
swarmcfo/
├── apps/web/           # Next.js (big screen + phone)
├── spacetime/          # Rust/TS SpacetimeDB module
├── agents/             # FastAPI + Anthropic tool-use agents
├── packages/shared/    # Shared types / constants
├── poc/                # Offline deterministic demo
├── data/seed/          # Bakery ledger generator + JSON
├── .env.example
└── package.json        # npm workspaces
```

## Quick start

```bash
cp .env.example .env
# fill ANTHROPIC_API_KEY (and optional Stripe test keys)

npm install

# Terminal A — SpacetimeDB (requires spacetime CLI)
npm run spacetime:publish

# Terminal B — agent service
python -m venv .venv && .venv\Scripts\activate   # Windows
# source .venv/bin/activate                      # macOS/Linux
pip install -r agents/requirements.txt
npm run agents

# Terminal C — web
npm run dev
```

**Offline fallback** (judges / dead Wi-Fi):

```bash
npm run sim
```

## Team split (36h)

| Role | Owns |
| --- | --- |
| SpacetimeDB / state | Tables, reducers, subscriptions |
| Agents / prompts / tools | Five Claude agents + arbitration |
| Frontend world + phone UX | Big screen, QR join, Approve |
| Data + demo + Devpost | Seed ledger, rehearsals, video before final hour |

## Sponsor fit

- **Hyphenate** — Autonomous Systems for Finance  
- **Creao** — Best One-Person Company  
- **SpacetimeDB** — realtime multiplayer shared state  
- **CRS** — Best Financial AI Agent  
- **Anthropic** — five distinct Claude agents with tools  

## License

MIT — CalHacks 13.0
