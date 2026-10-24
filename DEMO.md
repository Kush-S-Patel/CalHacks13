# SwarmCFO — Hyphenate demo script (3 minutes)

## Pre-flight

```bash
pip install -r agents/requirements.txt
cd agents && python -m sow.scenario   # expect SCORE 100/100
uvicorn main:app --port 8000
# other terminal
npm run dev
```

Record fallback video of `sow.scenario` before the final hour.

## Talk track mapped to judging

### 0:00–0:25 — Real enough
> “Maya’s Bakery. One person. Eleven days of runway. We’re not replacing her bank or QuickBooks — we sit on top as the **system of work**.”

Show runway. Mention systems of record vs system of work (workshop slide).

### 0:25–0:50 — Self-learning
> “At onboarding we queried a year of short wires. **pol-001**: gap ≤ $50 → book to 6850 Bank Fees. Evidence: seven precedents. Maya approved the policy — not a prompt.”

Flash Policy panel.

### 0:50–1:15 — Graphs (complicated company)
Open `/graphs` or the Company graph on the world page.

> “This is not a toy ledger. Full supply chain — wheat co-op to Harbor Cafe — with **exact dollars** on every edge. Red dashed = fraud. Amber = hold.”

Flip tabs: **Supply chain** → **Context** → **Relationships**. Click the FRAUD $4,200 edge.

### 1:15–1:50 — Team + limits (would you hire it?)
Press **Run full demo** (graphs refresh live).

Call out on the audit feed:
1. Short wire → **ASK** → Maya answers → gateway **POST**  
2. Duplicate $4,200 → **BLOCK** · show **DENIED** when Risk tries to approve  
3. Procurement vs Risk → CFO **arbitrate**  
4. Cashier **cannot** approve $1,400 — **HELD**

> “Limits are in `can()`. Denied attempts are logged. Only the gateway posts.”

### 1:50–2:25 — Wow + handles a no
Owner phone: **Approve** $1,400. Runway jumps. Fraud edge stays red on the graph; hold turns posted. Score → 100.

Mention rejection of sketchy supplier → precedent → **pol-014** drafted (self-improving).

### 2:25–3:00 — Close
> “Two thousand students here will start something alone. None can hire a finance team. This is the team — and every call is queryable months later.”

Optional: hit `/v1/audit/inv-dup-incoming` on screen.

## Answer key

See `agents/sow/scenario.py` → `ANSWER_KEY` and `poc/last_sow_run.json`.

## Weak patterns we explicitly avoid

- Chatbot over a spreadsheet  
- Ten shallow workflows  
- Happy-path-only data  
- “The prompt tells it not to”  
- Memory that dies with the context window  
