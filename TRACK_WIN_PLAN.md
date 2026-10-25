# Cal Hacks 13.0 — Sponsor Track Win Plan

**Project:** SwarmCFO Claims

**Goal:** Win sponsor tracks. Every feature below must strengthen a judging requirement or the live demo.

**Primary target:** Hyphenate

**Secondary targets:** Microsoft, Anthropic, Apify

**Conditional target:** Capital One / Nessie, only if a live API call works quickly

**Submission deadline:** Sunday, October 25, 2026 at 9:00 AM PDT

**Product-facing rule:** The judged UI must never look like a sponsor checklist. Do not put the words Hyphenate, Microsoft, Anthropic, Apify, Capital One, Nessie, or track names in the primary product experience. Show the capabilities as `Source current`, `Rule interpreted`, `Claim checked`, `Human decision`, `Policy learned`, and `Approval proven`. Provider names and IDs belong in sponsor-specific Devpost sections, the README, and an optional collapsed technical-provenance drawer.

## 1. The Product We Are Building

SwarmCFO Claims is a governed reimbursement agent for workforce-development nonprofits.

It retrieves an official grant rule, uses Claude to turn that rule into a cited structured policy, matches a nonprofit's ledger and receipts against live payment evidence, pauses on ambiguity, records a real manager decision, and turns that correction into a durable guardrail for the next claim. The AI can prepare and recommend a claim, but only an authorized human can approve it.

### The winning demo story

1. Apify retrieves and versions an official grant-rule page.
2. Claude extracts the relevant rule with an exact quote, source, confidence, and ambiguity flag.
3. The deterministic Claims engine checks nine ledger lines, receipts, dates, duplicates, and payment evidence.
4. The system asks a manager whether an ambiguous **$860 catering expense** is reimbursable.
5. The manager answers **No** and gives a reason.
6. The system revises the claim, records the decision as precedent, and proposes a policy.
7. The manager separately approves that policy.
8. A new next-month claim with a similar expense is automatically held.
9. An AI approval attempt is denied by code; an authorized manager approves the corrected claim.
10. The audit trail shows the source, model result, evidence, human decisions, policy version, denied action, and final approval.

### Target result shown to judges

- Original GL: **$36,295**
- Excluded/protected: **$8,160**
- Eligible claim: **$28,135**
- Reconciliation gap: **$0**
- Critical exceptions after correction: **0**
- Unauthorized approvals: **0**

The arithmetic, generated schedules, risk score, status, and UI must all agree with these numbers.

---

## 2. Track Strategy

| Priority | Track and verified prize | Judging direction / workshop guidance | Track-neutral visible proof | Submission / technical proof | Hard gate |
|---|---|---|---|---|---|
| 1 | **Hyphenate — $8K / $5K / $3K; expedited interview process for top five** | Autonomous finance; workshop guidance emphasizes one messy business corner implemented deeply, an agent that asks at the right time and handles a human **No**, code-enforced limits, recorded decisions and a credible stage moment | A typed manager decision changes the claim, becomes a separately approved policy, holds a genuinely separate future claim, and the AI approval attempt is denied | Restart test, state-transition history, append-only allowed and denied audit records | No one-click scripted chain, automatic policy approval, context-only memory, or contradictory math |
| 2 | **Microsoft — Surface laptops, FDE tech talk, mentorship** | Customer understanding, measurable usefulness, prototype-to-production path, responsible design, and end-to-end functionality | One complete nonprofit claim journey, clear human control, measurable claim dollars, safe failure behavior and auditability | Truthful customer evidence note and production-path write-up. Microsoft technology is explicitly not required | Do not claim real customers, savings, or validation without evidence |
| 3 | **Anthropic — $5K credits, Max 20x, office hours, HQ visit** | A narrow named community, a real problem, a working high-impact product, impact measurement, and thoughtful Claude use in development and product operation | Exact rule quotation, source link, concise reasoning, confidence and a real ambiguity routed to a person | Live model/request receipt, strict structured output, prompt/output excerpt and literal citation verification | Claims must call live Claude; never present a stub or fixture as live |
| 4 | **Apify — $2K / $1K / $800 / $400 / $400; separate $400 Actor prize** | Meaningful use of live web data to automate a workflow or power an agent | Current official source, retrieval timestamp, version hash, change state and a source-run receipt that actually affects the decision | Actor link/ID, run ID and dataset link/ID. A custom Actor does not need Store publication | A decorative scrape does not qualify; its output must feed the judged decision |
| 5 | **Capital One / Nessie — $1,200 total / $300 Giftogram per teammate on Devpost** | The official Slack post says only **Best use of the Nessie API**; the four-field match below is our design choice, not a stated sponsor requirement | A live payment transaction is matched by amount, vendor, date and reference; a mismatch creates a hold; a paid expense can still be ineligible | Repeatable API request/response receipt and real sandbox account/transaction IDs | Enter only if a live Nessie call works quickly and materially affects Claims; the bakery demo does not qualify |

### Reuse without extra engineering

Submit the same finished product to these broad categories if allowed by the submission form:

- People-First Social Impact
- Overall
- Most Creative
- Most Technically Advanced Hack
- Hacker's Choice

Do not add unrelated features merely to fit another sponsor.

---

## 3. Current Repository Truth

**Recovery update, October 24, 2026:** The guided UI and interrupted source edits have been recovered on top of upstream `8dbc5c2`. SQLite work-state persistence and independent next-period submission are implemented. The real HTTP workflow passed two backend process restarts. A private rule-watcher Actor was built successfully, and an actual Apify run fed a live Claude interpretation with a verified quote and a human-review question. See `RECOVERY_STATUS.md` for current evidence and remaining boundaries. Older implementation notes below describe the pre-recovery checkpoint and are retained for planning history.

### What already works

- A synthetic workforce-development nonprofit claim with nine ledger lines and evidence.
- Deterministic transaction/evidence matching, duplicate detection, reporting checks, risk scoring, schedules, and totals.
- A Claims UI with KPIs, a story timeline, revision comparison, checks, and audit display.
- Code-enforced role permissions and a visible denied AI approval attempt.
- Claim-package JSON persistence.
- A generic Anthropic SDK runtime elsewhere in the application.
- A real Nessie HTTP client and sandbox provisioning helpers.
- The recovered backend suite and added recovery regressions cover the guided workflow, separate decisions, persistence/reload, provider failure handling, source hashing, literal citations, and saved refresh results. Use `scripts/test_backend.py` for the current count and an isolated run.
- The production frontend build passes, including `/_not-found` and `/demo`.
- A focused, sponsor-neutral `/demo` route now shows the human decision, exception-first lines, authoritative source excerpt, reconciliation KPIs, proof rail, and audit timeline.
- Final package math now agrees everywhere: **$36,295** ledger, **$28,135** eligible, **$8,160** held out, and **$0** reconciliation gap.
- Generated schedules exclude held-out rows, risk uses the true reconciliation gap, and the final schedule carries the final status.
- The judged flow now uses separate API actions for the manager decision, each remaining exception, policy proposal, policy approval, denied AI approval attempt and final manager approval.
- Both `Exclude` and `Allow with documented exception` are real backend branches with a required reason; the manager decision changes only the catering line.
- The revision-2 approval work item is synchronized to the corrected **$28,135** claim before approval.
- A fail-closed Apify source adapter and a strict Claims-specific Claude interpreter are implemented and unit-tested, but not yet connected to the live judged path.

### Historical gaps at the pre-recovery checkpoint

- Work items, precedents, policies, and audit events are stored in memory and disappear after restart.
- The future-claim hold is a synthetic step inside the original script, not a separately submitted claim.
- Claims does not yet invoke the new Claude interpreter from a route or the judged workflow.
- The Apify adapter is not yet wired to a refresh endpoint, configured with live credentials, or backed by a completed Actor run.
- Nessie is connected to an unrelated Maya's Bakery demo, not Claims.
- Existing automated tests do not cover a real restart, an independent future claim, or live provider calls.
- The older `/suite/claims` screen remains crowded with a full-loop button, answer-key language, raw JSON, raw Markdown, risk/corpus charts, history, and logs; use `/demo` for judging.
- The shared suite navigation visibly exposes unrelated product areas and a provider badge.
- Some README/demo language still describes the bakery rather than the Claims product.

**Current conclusion:** Durable guided state, an independent later claim, and the live Apify-to-Claude path have now been verified. Claims-specific Nessie matching, actual receipt-file verification, production authentication, customer validation, and final submission/video remain unverified or unfinished.

---

## 4. Final Architecture

```text
Official grant-rule URL
        |
        v
Apify Grant Rule Watcher
URL + fetched_at + content_hash + changed + Actor/run/dataset IDs
        |
        v
Claude structured rule extraction
rule + exact_quote + source_url + confidence + needs_human + suggested_question
        |
        v
Deterministic Claims engine <--- ledger + receipts + optional Nessie transactions
        |
        v
Real manager decision
        |
        v
Persistent precedent + proposed policy + separate manager policy approval
        |
        v
Independent next-month claim automatically held
        |
        v
AI approval DENIED -> manager approval -> append-only audit
```

### Responsibility boundaries

- **Claude:** Interpret unstructured rule text, cite exact language, identify ambiguity, and propose a question.
- **Apify:** Retrieve and version the current public source.
- **Deterministic code:** Money math, matching, eligibility checks, state transitions, permission checks, and reconciliation.
- **Human manager:** Resolve ambiguous policy questions and approve policies/claims.
- **Nessie:** Provide external payment evidence only; a payment does not automatically make an expense reimbursable.

---

## 5. Competitor-Informed Product Experience

### Position to protect

SwarmCFO is **not** another corporate-expense app, grant CRM, generic chatbot, or full accounting suite.

> **SwarmCFO is a post-spend grant-reimbursement workspace that converts ledger activity into an evidence-backed claim, pauses for human judgment, learns a separately approved policy, and produces an auditable submission package.**

### Patterns to adapt, not copy

| Reference | What is useful | SwarmCFO adaptation | Do not copy |
|---|---|---|---|
| [Ramp Policy Agent](https://support.ramp.com/policy-agent-overview/) | Recommendation and important findings first; exact cited policy text; transaction context; reviewer override and policy version | Put `Ready`, `Evidence needed`, or `Human decision` at the top of the selected expense; show documentation, rule, business-purpose and payment checks directly underneath | Ramp's colors, layout, icons, terminology, auto-approval positioning or marketing claims |
| [GrantGuard](https://www.grantguard.ai/) | Requirement beside its exact source clause; grant budget and documents in context | Put the official quotation, URL, retrieved time, rule version and receipt/payment evidence next to the selected line | Its visual identity or a generic compliance-health score as the hero |
| [AppZen Expense Audit](https://www.appzen.com/travel-and-expense-overview) | Check every line but send humans only meaningful exceptions; keep a decision record | Analyze all nine lines, show exception rows first, and collapse clean rows under `5 checks passed` | Enterprise breadth, unsupported accuracy/ROI claims or an autonomous-approval story |
| [Blackbaud grant accounting](https://www.blackbaud.com/products/blackbaud-financial-edge-nxt/grant-and-program-accounting) | Grant-specific record, reimbursement status, controls and transaction drill-down | Keep organization, award, period, revision and financial reconciliation visible in the claim header | A large ERP information architecture |
| [Sage Intacct Grants](https://www.sage.com/en-us/sage-business-cloud/intacct/product-capabilities/extended-capabilities/grants-tracking-billing/) and [Workday Grants](https://www.workday.com/en-us/products/financial-management/grants-management.html/) | Reimbursable-cost workflow, unallowable-cost controls, approval boundaries and auditability | Use a finance-manager-only workspace with explicit eligibility and approval states | Unrelated accounting modules, dashboards or navigation |

Borrow interaction principles only. Do not reuse screenshots, logos, copy, proprietary labels, claimed accuracy, or competitor visual styling. Keep SwarmCFO's forest/cream identity and unique revision → policy → future-case learning loop.

### The one judged page

Create a distraction-free `/demo` route. The page is one guided claim workspace, not six dashboards.

| Region | What judges see |
|---|---|
| Header | `SwarmCFO Claims` · organization · award · reporting period · revision · current status · `Official source checked 2 min ago` |
| Six-step strip | `Source current → Rule interpreted → Claim checked → Human decision → Policy learned → Approval proven` |
| KPI strip | Original ledger **$36,295** · Eligible **$28,135** · Excluded/protected **$8,160** · Reconciliation gap **$0** |
| Claim-line panel | Exception rows first; North Bay Catering $860 selected; clean rows collapsed under `5 checks passed` |
| Decision workspace | System recommendation, exact official quote, short reasoning, receipt and payment evidence, missing context, required reason, `Exclude` and `Allow with documented exception` |
| Proof rail | Source receipt, interpretation receipt, payment receipt, policy version and approval/audit receipt using neutral labels |
| Bottom timeline | Claim revised → policy proposed → separate owner approval → independent October claim held → automated approval denied → manager approval → package ready |

The key copy beside payment evidence is: **“Payment verified. Reimbursement eligibility remains unresolved.”** This is the simplest way to show that bank evidence and grant eligibility are different questions.

### What disappears from the primary demo

- The paragraph that explains the entire story before it happens.
- The `Full loop` button.
- `Learning-loop checks 100/100` and `Answer-key checks` language.
- Raw revision JSON, raw agent logs and raw Markdown package.
- The large rejection-risk/corpus visualization.
- Accumulated claim history.
- Generic ERP navigation, graphs, jobs, bakery surfaces and visible sponsor/provider badges.

These can remain behind a development route or collapsed `Technical receipts` drawer, but never compete with the $860 decision.

### Exact frontend implementation

- Create `apps/web/src/app/demo/page.tsx` with a minimal presentation layout.
- Refactor `ClaimsPanel.tsx` into small product components: `ClaimHeader`, `ReviewStepper`, `ClaimLineList`, `HumanDecisionPanel`, `ProofRail`, `PolicyApprovalPanel`, `OutcomeStrip`, and `AuditReceiptDrawer`.
- Keep the first render on **Human decision**, because that is the emotional and product-defining moment.
- Let Previous/Next move through proof states, but every completed state must come from backend data—not hard-coded UI text.
- Animate only the revision dollars and step advancement. Avoid decorative motion.
- Make the route usable at 1024×768 and on a laptop without scrolling during the core three-minute flow.

---

## 6. Build Plan in Required Order

### P0 — Live credential gate (maximum 30–45 minutes)

Before building integrations, prove each provider works with one real call.

- [ ] One successful Anthropic API call from the project environment.
- [ ] One successful Apify Actor run and dataset read.
- [ ] Select one official public rule source, preferably **2 CFR § 200.438** or another page directly relevant to the ambiguous catering/entertainment expense.
- [ ] Add `APIFY_TOKEN` and `APIFY_ACTOR_ID` configuration.
- [ ] One successful Nessie API call.

**Decision rule:** If Nessie is not working by the end of this gate, drop the Capital One track and move that developer to core reliability. Never present a cache, fixture, or failed call as live.

### P1 — Fix objective financial correctness

This is the first code change because contradictions will damage every track.

- [x] Exclude every `excluded_from_claim` line from claimed budget totals.
- [x] Reconcile as `eligible + excluded = original GL`.
- [x] Use the calculated reconciliation gap in risk scoring.
- [x] Rebuild schedules after the final status changes.
- [x] Make the status, risk, schedules, package, and KPI cards agree on the final package.
- [ ] Rename the visible period check accurately: outside the monthly reporting window is not automatically outside the full award period of performance.
- [x] Keep answer-key language out of the judged `/demo` route.
- [x] Show the authoritative 2026 CFR excerpt and label it honestly as a bundled snapshot with live refresh pending.

**Acceptance test:** The UI and exported package both show $28,135 eligible, $8,160 excluded, $36,295 original GL, and $0 gap with no contradictory status.

### P2 — Replace the scripted Hyphenate demo with a real state machine

Use explicit, persisted states:

```text
DRAFT
  -> ANALYZED
  -> NEEDS_MANAGER_DECISION
  -> REVISED
  -> POLICY_PENDING_APPROVAL
  -> READY_FOR_APPROVAL
  -> APPROVED
```

Build separate user actions/endpoints:

- [x] Start claim review.
- [x] Show the unresolved question without answering it.
- [x] Accept real manager input: `Allow` or `Exclude`, plus a written reason.
- [x] Generate revision 2 from that decision only.
- [x] Propose a precedent and policy.
- [x] Require a separate manager action to approve the policy.
- [ ] Submit a separate next-period claim.
- [ ] Evaluate it against the approved policy.
- [x] Attempt AI approval and display the denied result.
- [x] Allow only the authorized manager to approve the claim.

Important correctness rule: the catering answer may only change the catering decision. Duplicate removal, missing receipt handling, and date correction must each have their own evidence or explicit resolution.

**Current acceptance:** A judge can stop after the question, enter either answer, resolve each remaining line separately, approve the proposed policy separately, prove the AI denial and approve the synchronized revision-2 package. Future-claim behavior remains unproved until the independent next-period endpoint exists.

Recommended API split:

```text
POST /v1/claims/reviews                         start and analyze a claim
POST /v1/claims/{id}/rules/refresh              retrieve and version the public rule
POST /v1/claims/{id}/decisions                  {decision, reason}
POST /v1/claims/{id}/exceptions/{line_id}/resolve
POST /v1/policies/{id}/approve                  separate policy-owner action
POST /v1/claims                                 submit the independent next-period claim
POST /v1/claims/{id}/approval-attempts          show the agent denial
POST /v1/claims/{id}/approve                    authorized manager action
GET  /v1/claims/{id}/audit                      reproduce the complete chain
```

Do not keep extending the monolithic `phase=resume` call. Each endpoint must validate the actor role, expected current state, idempotency key and required reason before mutating state.

### P3 — Make organizational memory durable

Use SQLite or append-only JSONL under the existing ERP vault. Do not add another sponsor database.

Persist:

- [ ] Work items and state transitions.
- [ ] Human questions and answers.
- [ ] Claim revisions.
- [ ] Precedents.
- [ ] Proposed and approved policy versions.
- [ ] Actor/model/source provenance.
- [ ] Approval and denial attempts.
- [ ] Append-only audit events with actor, role, timestamp, before/after state, and reason.

All mutation must go through the audited transition layer. Do not mutate payload fields after an audit event has been recorded.

**Acceptance test:** Restart the backend. Submit the next-month claim. The previously approved policy still exists and automatically holds the similar expense.

### P4 — Add the Apify Grant Rule Watcher

Build one custom Actor with a deliberately narrow job.

**Input**

```json
{
  "urls": ["https://official-source.example/rule"],
  "previous_hash": "optional"
}
```

**Output**

```json
{
  "source_url": "...",
  "title": "...",
  "clean_text": "...",
  "fetched_at": "...",
  "content_hash": "...",
  "changed": true,
  "actor_id": "...",
  "run_id": "...",
  "dataset_id": "..."
}
```

- [x] Adapter fails closed for invalid/private URLs, request failure/timeout, failed runs, malformed output and empty extraction.
- [ ] Save the Actor, run, and dataset identifiers with the claim review.
- [ ] Make **Refresh Rules** trigger a real run.
- [ ] Feed the returned text into Claude; do not use a bundled copy on the judged path.
- [ ] On failure, hold for human review rather than silently using stale data.

**Acceptance test:** A judge clicks Refresh Rules and sees a new live timestamp/run ID; that data is consumed by the Claims decision.

### P5 — Put Claude inside the Claims decision path

Claude must perform a narrow, necessary task rather than acting as a generic chatbot.

Require strict structured output:

```json
{
  "rule": "...",
  "exact_quote": "...",
  "source_url": "...",
  "confidence": 0.0,
  "needs_human": true,
  "suggested_question": "..."
}
```

- [x] Add a Claims-specific prompt and strict interpreter adapter.
- [x] Accept the exact retrieved `clean_text` and trusted `source_url` as context.
- [x] Require an exact quote, not an invented citation.
- [x] Verify in deterministic code that `exact_quote` literally exists in the retrieved text.
- [x] Reject invalid schema, changed source URL or unverifiable quotes.
- [ ] Route low-confidence or ambiguous results to a human.
- [ ] Main UI shows the source URL, generic live-call receipt, exact quote and confidence; the collapsed technical drawer stores the model name/request metadata for track proof.
- [x] Ensure missing credentials and API failures fail closed; never label the adapter as a live call.

The checked items above are adapter-level capabilities with mocked tests. The route, live credentials, Apify-to-Claude wiring, stored receipt and UI state remain required.

**Acceptance test:** Claude returns a verifiable cited rule from the current Apify dataset, and its ambiguity output creates the real manager question.

### P6 — Connect Nessie to Claims only if the credential gate passed

Replace the bakery story with nonprofit payment evidence.

- [ ] Provision or reuse a nonprofit customer and **Grant Operating** account.
- [ ] Seed or reuse sandbox withdrawals matching the claim scenario.
- [ ] Store `ledger_line_id -> Nessie transaction_id`.
- [ ] Match by amount, date, reference, and vendor.
- [ ] Put Nessie transaction IDs into the evidence view and audit.
- [ ] Hold any claim line with missing or mismatched bank evidence.
- [ ] Make repeated demo runs idempotent or reuse existing records.
- [ ] Never mark a failed API call as successful Nessie use.

Strong demo evidence:

- One **$5,200** Nessie withdrawal compared with two **$5,200** GL rows proves a duplicate.
- The **$860 catering** payment can exist in Nessie but still be excluded: **paid does not mean reimbursable**.

**Acceptance test:** A visible live transaction ID affects the claim, and a deliberate mismatch creates a hold.

### P7 — Wire one track-neutral judge screen to real state

The judged route must contain only these six product stages:

1. **Source current:** official URL, fetch time, content hash and a generic source-run receipt.
2. **Rule interpreted:** exact citation, short reasoning, confidence, ambiguity and suggested question.
3. **Claim checked:** ledger, receipt and payment-transaction match.
4. **Human decision:** a genuine choice and required reason.
5. **Policy learned:** precedent, proposed policy, separate owner approval and independent next-period hold.
6. **Approval proven:** denied automated approval, authorized manager approval, audit and financial metrics.

Keep provider names out of the primary page. Put Actor/model/bank API identifiers inside a collapsed **Technical receipts** drawer for sponsor Q&A and in the submission. Hide bakery, generic missions, graphs, ERP experiments and unrelated agents from the judged route.

**Acceptance test:** A new judge understands the problem, evidence, human decision, learned policy, and safety boundary without visiting another page.

### P8 — Add evidence, tests, and submission material

- [ ] Add a short customer evidence note: who the user is, what was learned, and what changed in the product.
- [ ] Add an architecture diagram and a truthful prototype-to-production section.
- [ ] Update README and demo language to use only SwarmCFO Claims.
- [ ] Document setup and required environment variables.
- [ ] Record the live provider IDs needed for Devpost.
- [ ] Prepare sponsor-specific Devpost sections instead of one generic paragraph.
- [ ] Record a backup three-minute video after the demo succeeds twice in a row.

---

## 7. Team Assignment

| Owner | Primary responsibility | Definition of done |
|---|---|---|
| **A — Core / Hyphenate** | Financial fixes, state machine, persistence, RBAC, audit | Human correction is real, policy survives restart, future case is held, unauthorized approval is denied |
| **B — Intelligence** | Apify Actor, Claude extraction, citation verification, provider proof | Live Apify output creates a verified Claude rule and a human question; failures hold safely |
| **C — Evidence / Reliability** | Nessie if viable, backend tests, idempotency, failure cases | Live transaction affects a claim, or Nessie is cleanly cut; critical tests pass |
| **D — Judge Experience** | One-screen UI, Microsoft/customer evidence, README, Devpost, video, pitch | Three-minute demo is clear, truthful, rehearsed, and submission-ready |

Merge and demo the integrated branch every two hours. No owner should work for the full night without showing an integrated result.

---

## 8. Relative Sprint Schedule

| Time | Goal |
|---|---|
| **0:00–0:30** | Provider credential gate and official source selection |
| **0:30–3:00** | Parallel work: core state/persistence, Apify+Claude, Nessie/test harness, judge UI |
| **3:00–4:00** | First full integration; cut Nessie if it threatens the core |
| **6:00–7:30** | Automated tests and two uninterrupted demo rehearsals |
| **7:30–9:00** | Backup video, README, Devpost answers, screenshots, final freeze |

### Hard checkpoint

By the first integration checkpoint, the project must have:

- Correct financial output.
- A real manager decision.
- A separately approved persistent policy.
- A separately submitted future claim that is held.
- A logged denied AI approval.

If any of these are missing, stop secondary work and finish the Hyphenate core.

---

## 9. Required Test Matrix

- [x] Real human input changes revision 2.
- [x] One manager decision does not silently fix unrelated exceptions.
- [x] Excluded lines never appear in claimed schedule totals.
- [x] Final `eligible + excluded = original GL` and gap is zero.
- [x] AI/agent approval fails at the permission boundary.
- [x] Manager approval succeeds and is audited against the synchronized revision-2 work item.
- [x] Approved policy survives backend restart.
- [x] A separately submitted next claim is held by that policy.
- [x] Unit test proves Claude's exact quote must exist verbatim in retrieved text.
- [x] Unit tests prove invalid Claude schema, changed URL and invented citation fail closed.
- [x] Unit tests prove failed/empty/malformed Apify results fail closed.
- [ ] Missing or mismatched Nessie evidence creates a hold, if Nessie is enabled.
- [ ] Repeated provider/demo actions do not duplicate records unexpectedly.
- [x] Complete current-claim happy path reaches approved with consistent status everywhere.
- [x] Production frontend build passes.

### Minimum evaluation cases

1. Valid wages.
2. Valid fringe.
3. Missing receipt.
4. Duplicate ledger line.
5. Outside reporting window.
6. Ambiguous catering/celebration expense.
7. Missing bank transaction.
8. Repeat celebration expense after approved policy.

---

## 10. Three-Minute Track Demo

| Time | What happens | Track proof |
|---|---|---|
| **0:00–0:20** | Explain the nonprofit reimbursement problem and why delay/errors hurt program delivery | Microsoft, Anthropic, People-First |
| **0:20–0:45** | Click Refresh Rules; show live Apify run, timestamp, hash, and dataset | Apify |
| **0:45–1:05** | Show Claude's verified quote, structured rule, confidence, and ambiguity | Anthropic |
| **1:05–1:25** | Show ledger/receipt evidence and, if live, Nessie duplicate/payment proof | Capital One, real-world evidence |
| **1:25–1:50** | Manager enters **Exclude** and explains why; revision updates | Hyphenate human correction |
| **1:50–2:10** | Manager separately approves the policy; next-month claim is automatically held | Hyphenate organizational memory |
| **2:10–2:35** | AI approval is denied; manager approves; audit records both attempts | Hyphenate safety, Microsoft responsibility |
| **2:35–3:00** | Show $8,160 protected, $28,135 eligible, $0 gap, zero unauthorized approvals, and provider proof | Measurable impact and close |

Do not narrate implementation details that are already visible. Spend time on the human correction, durable learning, and why each provider is necessary.

---

## 11. Definition of Done

The build is ready to submit only when all applicable statements are true:

- [x] The manager decision is genuine input, not a constant.
- [x] Policy approval is a separate human action.
- [x] The policy and audit survive a backend restart.
- [x] A new, independent next-period claim is held by the learned policy.
- [x] An unauthorized approval attempt is visibly denied and logged.
- [x] All financial totals, risk, status, schedules, work items and packages agree for the current claim.
- [x] A live Apify run/dataset materially affects the claim workflow.
- [x] Live Claude produces a verified source quote in the Claims path.
- [x] Provider failures fail closed to human review; mocked failure paths and persisted failure receipts are checked.
- [ ] A live Nessie transaction affects the claim, or the Capital One track is removed.
- [x] Automated current-path tests and the production build pass.
- [ ] The complete demo succeeds twice without manual database repair.
- [ ] README, video, screenshots, and Devpost answers match the actual build.

---

## 12. Explicit Cuts

Do **not** build any of the following before the definition of done is green:

- More finance workflows, agents, dashboards, graphs, or ERP modules.
- A generic chatbot.
- An OCR platform.
- More bakery features or migration of the bakery story.
- Automatic submission to a funder or automatic ledger writes.
- A new database solely to qualify for another sponsor.
- Figma, Moss, CREAO, Convex, SpacetimeDB, CRS, Cartesia, or another sponsor integration.
- Unsupported claims about customers, time saved, accuracy, or production readiness.
- Fake, cached, stubbed, or failed integrations presented as live.

The winning principle is **one difficult nonprofit claim workflow completed deeply and truthfully**, not many shallow integrations.

---

## 13. Live Track-Proof Ledger

Update this table whenever a pull request lands. `Partial` means code exists but the judged proof is not yet honest or complete.

| Build evidence | Current status | Hyphenate | Microsoft | Anthropic | Apify | Capital One | Next proof required |
|---|---|:---:|:---:|:---:|:---:|:---:|---|
| Deterministic claim analysis and four exception types | Built | ✓ | ✓ |  |  |  | Keep, but expose independent checks rather than a black-box score |
| Financial totals, schedules, risk and status all agree | **Built** | ✓ | ✓ |  |  |  | Regression assertions now cover totals, risk gap, budget-line schedules and final status |
| Genuine `Allow` / `Exclude` plus required reason | **Built** | ✓ | ✓ | ✓ |  |  | Both branches are tested; keep the decision reason visible in the judged flow |
| Separate per-line exception resolutions | **Built** | ✓ | ✓ |  |  |  | Duplicate, reporting month and receipt metadata are separate audited actions |
| Separate policy-owner approval | **Built** | ✓ | ✓ |  |  |  | Proposal and finance-manager approval use distinct endpoints and phases |
| Policy, work items and audit survive restart | **Verified** | ✓ | ✓ |  |  |  | SQLite plus two real Uvicorn process restarts |
| Independent next-period claim is held by approved policy | **Verified** | ✓ | ✓ |  |  |  | Separate October submission after restart |
| Automated claim approval denied by role enforcement | Built | ✓ | ✓ |  |  |  | Keep and show one denied receipt in the final timeline |
| Live official rule retrieval and version receipt | **Verified live** |  | ✓ | ✓ | ✓ |  | Actual private Actor/run/dataset IDs retained in RECOVERY_STATUS.md |
| Live cited rule interpretation with literal quote verification | **Verified live; human review requested** |  | ✓ | ✓ | ✓ |  | Real model question and exact quote saved to the claim |
| Live payment transaction affects eligibility workflow | **Missing** |  | ✓ |  |  | ✓ | Nessie transaction match or mismatch must change a line state |
| Focused, sponsor-neutral `/demo` workspace | **Built** | ✓ | ✓ | ✓ | ✓ | ✓ | Keep live provider states honest; the UI explicitly marks source refresh and payment matching as pending |
| Honest customer evidence and production path | **Missing / unverified** |  | ✓ | ✓ |  |  | Add only if based on a real conversation; label demo-dollar metrics synthetic |
| Critical tests and production frontend build | **Verified for recovered path** | ✓ | ✓ | ✓ | ✓ |  | See RECOVERY_STATUS.md and verification scripts for current results |

### Final target selection rule

- Always submit **Hyphenate** if the core state machine, persistence and audit gates are green.
- Submit **Microsoft** using the same finished core; it requires no extra sponsor integration.
- Submit **Anthropic** and **Apify** only when the live source → cited interpretation → human question chain works end to end.
- Submit **Capital One** only when a live Nessie transaction materially changes the Claims workflow.
- Broad categories may reuse the same product, but do not add unrelated functionality merely to enter them.

---

## 14. Official References

- [Cal Hacks 13.0 Devpost](https://cal-hacks-13-0.devpost.com/)
- [Hyphenate official Slack post](https://cal-hacks-13-0.slack.com/archives/C0C6TRFL8H3/p1792609139116729)
- [Microsoft official track brief](https://cal-hacks-13-0.slack.com/archives/C0C6X71NCEA/p1792795022826229)
- [Microsoft confirmation that its technology is not required](https://cal-hacks-13-0.slack.com/archives/C0C6X71NCEA/p1792867355614679?thread_ts=1792867355.614679&cid=C0C6X71NCEA)
- [Anthropic official track post](https://cal-hacks-13-0.slack.com/archives/C0C6Z0DP4D8/p1792798675684999)
- [Apify official track post](https://cal-hacks-13-0.slack.com/archives/C0C7TGUC924/p1792528380692499)
- [Apify custom Actor qualification answer](https://cal-hacks-13-0.slack.com/archives/C0C7TGUC924/p1792872693169749?thread_ts=1792872693.169749&cid=C0C7TGUC924)
- [Capital One / Nessie official track post](https://cal-hacks-13-0.slack.com/archives/C0C6HQPNJET/p1792802652433309)
- [Organizer confirmation on entering multiple relevant tracks](https://cal-hacks-13-0.slack.com/archives/C0C6X34TC6A/p1792864196959139?thread_ts=1792863629.856729&cid=C0C6X34TC6A)
