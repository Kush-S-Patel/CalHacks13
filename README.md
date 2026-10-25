# SwarmCFO Claims

A reimbursement-review workspace for nonprofit bookkeepers. The guided `/demo` page preserves the recovered cream-and-green interface, exception-first review, separate manager approvals, future-policy proof, and audit timeline.

## Run locally

Use Node 20+ and Python 3.11+.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r agents/requirements.txt
npm ci
```

Create an ignored root `.env` from `.env.example`. Configure only the services you intend to use. Do not commit keys.

Terminal 1:

```bash
cd agents
../.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8877
```

Set `NEXT_PUBLIC_AGENT_API=http://127.0.0.1:8877` in `apps/web/.env.local` before building or starting Next.js. In terminal 2, from the repository root:

```bash
npm run dev -w @swarmcfo/web -- --port 3100
```

Open **http://127.0.0.1:3100/demo**. The homepage also links to guided review. The older suite and one-request endpoints remain for compatibility; `/demo` is the presentation path.

For a production preview, use `npm run build`, then `npm run start -w @swarmcfo/web -- --port 3100`.

## Guided review

1. Prepare September's seeded nine-entry ledger.
2. Optionally refresh the official rule through the live source/model pipeline.
3. Record Exclude or Allow with a reason for the $860 catering line. Allow retains the supporting-evidence requirement.
4. Resolve the duplicate, reporting-month, and receipt-reference issues independently.
5. Propose a future rule, read it, and approve it as a distinct manager action.
6. Submit a separate October claim and show its held work item under the approved policy.
7. Attempt automated approval and display the denied result.
8. Approve September as the manager. Load the actual audit receipts from the technical drawer.

The sample reconciles to **$36,295 raw ledger = $28,135 retained + $8,160 excluded**. The exclusions are a $5,200 duplicate, $2,100 October wages outside September's reporting month, and an $860 celebration. These are illustrative amounts, not savings or funder-approved payments.

## Live rule retrieval

Configure the ignored root `.env`, then restart the backend:

```dotenv
ANTHROPIC_API_KEY=your-key
CLAUDE_MODEL=an-available-model-id
APIFY_TOKEN=your-token
APIFY_ACTOR_ID=your-actor-id
```

The custom Actor source is in `integrations/grant-rule-watcher/`. It retrieves section 200.438 from the official GovInfo publication and returns normalized text, retrieval time, SHA-256 hash, change metadata, and source URL. The backend attaches real Actor, run, and dataset identifiers. Claude returns a structured interpretation whose quote must occur literally in the retrieved text. A request for human review changes the displayed question and remains visibly pending; it does not automatically allow the expense.

`scripts/deploy_rule_watcher.py` creates/updates and builds this **private** Actor using the configured account. It does not publish to the Store. Running it uses that account's cloud resources.

A live retrieval and Claude interpretation were verified during recovery. Mocked failure-path tests also exist. See `RECOVERY_STATUS.md` for the distinction and receipts.

## Storage and checks

Claim packages persist as JSON under `data/erp_vault/claims/`. Guided work items, policies, precedents, and audit associations persist in `data/erp_vault/guided_sow.sqlite3`. `SWARMCFO_CLAIMS_DIR` and `SWARMCFO_GUIDED_DB` override these locations for isolated verification.

```bash
.venv/bin/python scripts/test_backend.py
.venv/bin/python scripts/verify_claims_restart.py
npm run build
```

The first command isolates tests from a running demo. The second exercises real HTTP actions across two Uvicorn process restarts, checking policy reuse, an independent future hold, final approval, and retained audit IDs. It makes no provider calls.

## Current boundaries

- Personas, ledger, and receipt references are sample data. Linking a receipt record does not verify actual PDF bytes.
- Claims-specific Nessie evidence is not connected. Do not claim Capital One completion.
- Demonstrated role checks are code-level controls. Production authentication is not established.
- Stored policy matching uses a predefined template and deterministic conditions. There is no model retraining or general policy induction.
- Claim preparation never files with a funder, transfers money, or modifies the original ledger.
- The retrieved 2026 publication supports this synthetic demonstration, not a legal determination about a historical award.

See `DEMO.md` for the operator script and `RECOVERY_STATUS.md` for verified state. Actor references: [source files](https://docs.apify.com/actors/development/actor-definition/source-code), [create](https://docs.apify.com/api/v2/actors-post), [build](https://docs.apify.com/api/v2/actors-builds-post).
