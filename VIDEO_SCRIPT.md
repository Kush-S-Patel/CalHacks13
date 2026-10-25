# SwarmCFO Claims — video demo script

**Runtime:** ~2:45–3:15  
**Format:** screen recording + face optional (picture-in-picture)  
**URL:** http://127.0.0.1:3000  
**Tone:** calm, specific, no buzzword soup. One corner done deep.

---

## Pre-roll checklist (off camera)

```bash
npm run agents   # :8765
npm run dev      # :3000
```

1. Hard refresh `/`  
2. Confirm banner animates: Prepare → Ask → No → Learn → Prove  
3. Do **not** click Full loop before recording — use **Start — pause for Priya**  
4. Zoom browser to ~110% so dollars and DENIED are readable  
5. Hide bookmarks bar; cursor large if possible  

**Fallback:** if interactive fails mid-take, cut to a pre-recorded `phase:full` result screen and finish VO from “Handles a no.”

---

## Title card (0:00–0:05)

**On screen:** black / deep green  
**Lower third:** `SwarmCFO Claims`

**VO:**
> SwarmCFO Claims — a reimbursement package that learns from a no.

---

## Scene 1 — The problem (0:05–0:35)

**On screen:** Hero banner. Let the loop cycle once. Cursor idle.

**VO:**
> Outsourced bookkeepers prepare the same federal grant claim every month for nonprofits.
> Match the ledger to receipts. Catch duplicates. Decide what’s allowable.
> Agencies pay slowly. One wrong line costs weeks.
>
> We’re not the grant portal. We’re the system of work on top of it —
> for one messy corner: getting a claim ready for a finance manager to approve.

**Action:** Slow scroll so “Prepare → Ask → No → Learn → Prove” stays visible.  
**Lower third:** `Meridian Bookkeeping · Bay Area Workforce Collaborative`

---

## Scene 2 — How it works (0:35–0:55)

**On screen:** Scroll to **How it works**. Hover Ask → Learn → Prove.

**VO:**
> Three beats.
> Ask — when something is ambiguous, stop and ask a human.
> Learn — their no becomes a precedent, then a policy.
> Prove — limits in code, every transition audited.
>
> Done looks like this: eight thousand one hundred sixty dollars kept off the award…
> one hundred twenty-four dollars of missing receipt attached…
> twenty-eight thousand one hundred thirty-five eligible…
> four critical exceptions down to zero…
> and zero unauthorized approvals.

**Action:** Pause briefly on the dollar list so viewers can read.

---

## Scene 3 — Live demo: ask (0:55–1:25)

**On screen:** Scroll to **Live demo**. Click **Start — pause for Priya**.

**VO:**
> Meet Jordan, our Claims Agent, and Priya Shah, the finance manager.
> Jordan prepares September for Bay Area Workforce.
>
> Four problems show up in plain language —
> including an eight-hundred-sixty-dollar North Bay Catering charge.
> Is that a program lunch… or a staff celebration?
>
> Jordan doesn’t guess. He asks.

**Action:** Cursor on the amber Priya card. Zoom if needed so the question is readable.  
**Lower third:** `Jordan asks · Priya decides`

---

## Scene 4 — Handles a no → learns (1:25–1:55)

**On screen:** Click **No — staff celebration. Exclude it.**  
Don’t talk over the first second of motion — let story/KPIs appear.

**VO:**
> Priya says no. Exclude it.
>
> That isn’t a chat reply that disappears.
> Jordan rebuilds revision two.
> Eight thousand one sixty comes off the claim.
> The missing toner receipt gets attached.
> Twenty-eight thousand one thirty-five is what’s left eligible.
>
> Her correction is saved as a precedent…
> then proposed as policy — and Priya approves it.
> Next month’s celebration catering? Auto-held by that policy
> before it ever enters a package.

**Action:** Point at KPIs, then policy / next-month hold in the story.  
**Lower third:** `$8,160 excluded · $28,135 eligible · 4 → 0`

---

## Scene 5 — Would you hire it? (1:55–2:25)

**On screen:** Scroll to **Audit trail**. Find:
1. `ask` / Priya’s answer  
2. `revise_claim`  
3. `propose_policy` / `approve_policy`  
4. Jordan `approve` → **DENIED**  
5. Priya `approve`

**VO:**
> Watch the audit.
> Question. Answer. Revision diff. Policy version.
> Jordan tries to approve his own package — denied.
> Limits live in code, not in a prompt.
> Only Priya can approve.
> And this system never submits to the funder, and never changes the ledger.

**Action:** Hover DENIED so it reads clearly. Brief pause.

---

## Scene 6 — Something new + wow (2:25–2:50)

**On screen:** Back to demo results — Hyphenate YES chips + revision diff (or Claims suite risk viz).

**VO:**
> Judges ask four things.
> Is it real enough? Would you hire it? Is it new? Where’s the wow?
>
> Real: a workforce-grant claim with planted mess.
> Hireable: role limits, human in the loop, queryable audit.
> New: nonprofit claims that learn from a manager’s no —
> not another bakery short-wire demo.
> Wow: dollars kept off the award, next month already safer, score that backs the stage.

---

## Scene 7 — Close (2:50–3:10)

**On screen:** Hero brand again, or freeze on outcome line.

**VO:**
> Thousands of nonprofits wait on reimbursements.
> Fractional CFOs repeat this package across dozens of clients.
> SwarmCFO Claims prepares it, learns from a no, and proves every call.
>
> That’s the hire.

**End card (3:10–3:15):**
```
SwarmCFO Claims
Prepare · Ask · Learn · Prove
```

---

## Shot list (edit order)

| # | Shot | Duration |
| --- | ---: | ---: |
| A | Title card | 5s |
| B | Hero banner + loop | 25s |
| C | How it works trio + dollars | 20s |
| D | Click Start → Priya card | 30s |
| E | Click Exclude → KPIs / story | 30s |
| F | Audit DENIED close-up | 30s |
| G | Hyphenate chips / outcome | 25s |
| H | End card | 5s |

---

## B-roll / cutaways (optional)

- Zoom on “Waiting on Priya” counter flipping from 0 → 1  
- Policy panel showing `pol-claim-001` active  
- Revision diff JSON (1–2 seconds max)  
- Work queue row: `claim_policy_hold` · HELD  

---

## Words to avoid on camera

- “AI agent swarm” / “fully autonomous”  
- “We integrated NetSuite / Nessie” as the pitch  
- Bakery, short wire, account 6850, pol-001 / pol-014  
- “The prompt tells it not to approve”  

---

## Caption / subtitle cues (key lines)

1. “We’re the system of work — not the grant portal.”  
2. “Jordan doesn’t guess. He asks.”  
3. “Her no becomes precedent, then policy.”  
4. “Approve denied — limits in code.”  
5. “That’s the hire.”  

---

## 60-second cut (if judges demand short)

| Time | Do / say |
| ---: | --- |
| 0:00 | Banner: “Reimbursement that learns from a no.” |
| 0:10 | Start → show ask on $860 |
| 0:20 | Exclude → call $8,160 / $28,135 / 4→0 |
| 0:40 | Audit DENIED |
| 0:50 | “Learns, improves next month, proves it. That’s the hire.” |

---

## Recording notes

- One take for Scenes 3–5 if possible (the interactive beat is the wow).  
- If Exclude is slow, keep talking the dollar outcomes — UI will catch up.  
- Never narrate “clicking the button”; narrate *why* the decision matters.  
- End cold on “That’s the hire.” — no thank-you ramble.  
