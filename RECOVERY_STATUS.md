# Recovery verification — October 24, 2026

## Source and preservation

- Fresh clone: `Kush-S-Patel/CalHacks13`, upstream commit `8dbc5c28304f369ed1c1a811cd407748b6e34527`.
- Local branch: `codex/recover-claims-demo`.
- Recovered edits came from the supplied `i-x20.zip`, based on `78e2e7a`. They were compared with that base before restoration. No overlapping upstream application change required replacement.
- The cream/green `/demo` layout, exception list, reason field, proof rail, totals and timeline are retained. Upstream's homepage and banner are retained, with links into guided review.
- Work remains local unless explicitly pushed later. Credentials are in ignored local configuration, outside source exports.

## Verified complete

| Area | Evidence |
| --- | --- |
| Backend checks | 44 tests pass using isolated claim and SQLite stores |
| Frontend | Production Next.js build, type checking, and all 16 pages pass |
| Guided UI | Actual browser sequence reached manager-approved September package |
| Separate actions | Manager answer, three other line resolutions, policy proposal, policy approval, future submission, denied automated approval, and final approval use distinct actions |
| Financial result | $36,295 ledger = $28,135 retained + $8,160 excluded, gap $0 |
| Durable state | Real HTTP verification across two Uvicorn process restarts preserved policy, future held claim, final approval, and 24 audit events |
| Browser recovery | The real review was reloaded after stopping/restarting the running backend and retained its saved state |
| Live source | A private Apify Actor retrieved the official GovInfo section and produced a real dataset receipt |
| Live interpretation | A real `claude-sonnet-4-6` call consumed that text, produced a verified literal quote and a manager question, and requested human review |

The test count includes provider tests with mocks. The separate live run below establishes actual provider use; the unit suite alone does not.

## Live provider receipt

- Actor: `wUMIC6w2OaBSvG6V9` (private).
- Successful Actor build: `rkiGfMSC9Bhz9KULn`.
- Actual run: `eL0xIU9jJrohg2TNK`.
- Dataset: `sboundGH1aHF5AFtH`.
- Model: `claude-sonnet-4-6`.
- Supporting quote occurred literally in retrieved clean text.
- The interpretation requested human review. The UI displayed the generated question; the manager subsequently excluded the expense through the guided controls.
- The quoted source and receipts persisted across a backend restart.
- [Official source publication](https://www.govinfo.gov/content/pkg/CFR-2026-title2-vol01/xhtml/CFR-2026-title2-vol01-part200-subpartE.html).

No private credentials are needed in this report. Access to the private Actor's console still requires the owning account.

## Recovery fixes beyond the restored code

- Restored the missing Allow button and require an appropriate reason before allowing the catering line.
- Wired official-rule refresh into the existing UI, with truthful pending, failed, human-review, and manager-response states.
- Made refresh results and failures persist in claim JSON, in addition to audit artifacts.
- Added real audit receipt loading in the collapsed technical drawer.
- Preserve a saved browser review during temporary API failure instead of discarding its ID.
- Recover session handles from open work items when a cached session reference is missing.
- Display the proposed policy before separate approval and retain future-claim proof while advancing phases.
- Added configurable isolated storage, safe test runner, private Actor source/deployment helper, and a true process-restart verifier.

## Partial or not implemented

- Claims-specific Nessie/payment verification is not connected; a Nessie key was not supplied. The UI remains explicit about that. Do not claim Capital One completion.
- Receipt attachment links seeded metadata, not actual verified PDF bytes.
- Authentication remains a local prototype. Code-level role checks are not comprehensive production security.
- Policy creation uses a predefined template and deterministic matching. No model retraining or general policy induction is established.
- No funder filing, ledger mutation, money movement, measured customer savings, customer pilots, or final submission/video was performed.
- The private Actor has not been published to the Store. Sponsor access and final eligibility still need the team's confirmation.

No core failure was observed in the final backend/build/restart checks. These checks do not establish production readiness or cover every unrelated legacy ERP route.

## Reproduce

```bash
.venv/bin/python scripts/test_backend.py
.venv/bin/python scripts/verify_claims_restart.py
npm run build
```

Run instructions and the guided demo sequence are in README.md and DEMO.md. Use this report in preference to older “missing persistence” or “no live Claims integration” statements in historical conversations and planning notes.
