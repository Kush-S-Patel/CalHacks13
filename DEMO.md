# SwarmCFO Claims — stage demo (~3 minutes)

**Full video VO + shot list:** [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md)

Homepage flow: **banner (concept)** → **how it works** → **live demo (be Priya)** → **proof panels**.

## Pre-flight

```bash
npm run agents   # :8765
npm run dev      # :3000 → http://127.0.0.1:3000
```

Optional check:

```bash
curl -X POST http://127.0.0.1:8765/v1/claims/demo -H "content-type: application/json" -d "{\"phase\":\"full\"}"
# expect ok true, score 100, hyphenate 100
```

## Cast

| Who | Role |
| --- | --- |
| **Jordan** | Claims Agent — prepares, asks, never approves |
| **Priya Shah** | Finance Manager, Meridian Bookkeeping (you, on stage) |
| **Client** | Bay Area Workforce Collaborative · USDOL workforce grant |

## Homepage story (what judges see first)

1. **Hero banner** — full-bleed visual + animated loop: Prepare → Ask → No → Learn → Prove  
2. **How it works** — one corner: ask / learn / prove, with objective dollars  
3. **Live demo** — interactive pause for Priya’s no  
4. **Proof** — work queue, policies, append-only audit with diffs  

## Talk track × Hyphenate judging

### 0:00–0:35 — Real enough (hero + how it works)
Stay on the banner. Let the loop animate once.

> “Fractional CFO firm. Same messy September reimbursement every month. We’re not their grant portal — we sit on top as the **system of work** for the claim package.”

Scroll to **How it works**. Point at Ask / Learn / Prove.

### 0:35–1:05 — Asks at the right moment
Click **Start — pause for Priya**.

> “Jordan matched the GL. Four problems. The $860 catering charge is ambiguous — so the agent asks, instead of guessing.”

Gesture at the amber decision card.

### 1:05–1:40 — Handles a no + learns
Click **No — staff celebration. Exclude it.**

Call out as the story fills:
- **$8,160** kept off the award  
- **$124** receipt attached  
- **$28,135** eligible  
- precedent → **pol-claim-001**  
- October catering **auto-held**

> “Her no isn’t a chat message. It’s a precedent, then a policy she approves.”

### 1:40–2:15 — Would you hire it?
Scroll to **Audit trail**. Find Jordan’s approve → **DENIED**.

> “Limits are in `can()`. Denied attempts are logged. Only Priya approves. The system never submits to the funder.”

### 2:15–2:45 — Wow + something new
Show Hyphenate YES chips + revision diff.

> “Same narrow idea as reimbursement prep — but it learns, improves the next month, and proves every transition. Not a bakery short-wire clone.”

### 2:45–3:00 — Close
> “Outsourced bookkeepers repeat this corner across dozens of nonprofits. That’s the hire.”

## Weak patterns we avoid

- One-button planted flags with no manager beat  
- Leading with bakery / 6850 / pol-001 workshop twins  
- Ten shallow ERP tabs as the pitch  
- “The prompt says don’t approve”  
- Memory that dies with the context window  

## API

| Call | Purpose |
| --- | --- |
| `POST /v1/claims/demo` `{"phase":"start"}` | Pause for Priya |
| `POST /v1/claims/demo` `{"phase":"resume","answer":"No — that was our staff celebration. Exclude it."}` | Finish loop |
| `POST /v1/claims/demo` `{"phase":"full"}` | One-shot 100/100 |
| `GET /v1/claims/pending` | Recover interactive state after refresh |
