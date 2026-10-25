# SwarmCFO Claims — stage script (~3 minutes)

## Pre-flight

```bash
npm run agents   # :8765
npm run dev      # :3000
curl -X POST http://127.0.0.1:8765/v1/claims/demo -H "content-type: application/json" -d "{\"phase\":\"full\"}"
# expect ok true, score 100
```

## Cast

| Who | Role |
| --- | --- |
| **Jordan** | Claims Agent (`ai_claims`) — prepares, asks, never approves |
| **Priya Shah** | Finance Manager, Meridian Bookkeeping |
| **Client** | Bay Area Workforce Collaborative · USDOL workforce grant |

## Talk track × Hyphenate judging

### 0:00–0:30 — Real enough
> “Fractional CFO firm. Same messy September reimbursement every month. We’re not their grant portal — we sit on top as the **system of work** for the claim package.”

Hit **Start — pause for Priya**. Show four plain-language exceptions.

### 0:30–1:00 — Asks at the right moment
Jordan stops on **$860 North Bay Catering**.

> “The agent doesn’t guess entertainment. It asks Priya.”

Point at the amber decision card.

### 1:00–1:35 — Handles a no + learns
Click **No — staff celebration. Exclude it.**

Call out: revision 2 · **$8,160** off the award · **$124** receipt attached · **$28,135** eligible · precedent → **pol-claim-001**.

> “Her no isn’t a chat message. It’s a precedent, then a policy she approves.”

### 1:35–2:10 — Would you hire it? (limits)
October catering appears → **auto-held**. Jordan tries to approve → **DENIED** on the audit feed.

> “Limits are in `can()`. Denied attempts are logged. Only Priya approves. The system never submits to the funder.”

### 2:10–2:40 — Wow + something new
Flip revision diff + Hyphenate YES chips. Mention FAC / CA awards / 990 as **priors**, not the product.

> “Same narrow idea as ‘reimbursement prep’ — but it learns, improves the next month, and proves every transition.”

### 2:40–3:00 — Close
> “Outsourced bookkeepers repeat this corner across dozens of nonprofits. That’s the hire.”

Optional: `GET /v1/audit/{ask_work_item_id}` on screen.

## Weak patterns we avoid

- One-button planted flags with no manager beat  
- Bakery short-wire / 6850 / pol-001 as the lead (workshop echo)  
- Ten shallow ERP tabs as the pitch  
- “The prompt says don’t approve”  
- Memory that dies with the context window  

## API for judges

| Call | Purpose |
| --- | --- |
| `POST /v1/claims/demo` `{"phase":"start"}` | Pause at Priya |
| `POST /v1/claims/demo` `{"phase":"resume","answer":"No — that was our staff celebration. Exclude it."}` | Finish loop |
| `POST /v1/claims/demo` `{"phase":"full"}` | One-shot 100/100 |
