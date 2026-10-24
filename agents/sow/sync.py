"""
BUILD 1 — The environment.

Sync systems of record into one golden shape. Stateful, not a one-off export.
Change-only sync with a cursor per source. Stable ids so re-sync never duplicates.
Every golden row traces to its raw row.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sow.models import SYNC, GoldenRecord, now_iso
from sow.store import SystemOfWork


def stable_id(*parts: str) -> str:
    return hashlib.md5("|".join(parts).encode(), usedforsecurity=False).hexdigest()


def load_raw_ledger(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sync_into(sow: SystemOfWork, ledger: dict[str, Any], source: str = "bakery_ledger") -> int:
    """Land raw → standardised golden records. Idempotent via stable ids."""
    n = 0
    cursor_key = source
    prev = sow.sync_cursors.get(cursor_key)

    for inv in ledger.get("invoices", []):
        gid = stable_id("invoice", inv["id"])
        if gid in sow.golden:
            continue
        sow.golden[gid] = GoldenRecord(
            id=gid,
            kind="invoice",
            source=source,
            data={
                "invoice_id": inv["id"],
                "vendor": inv.get("vendor_name"),
                "amount_cents": inv["amount_cents"],
                "status": inv.get("status", "open"),
                "bank_fingerprint": inv.get("bank_fingerprint"),
                "due_date_iso": inv.get("due_date_iso"),
                "content_hash": inv.get("content_hash"),
            },
            raw_ref=inv["id"],
        )
        n += 1

    for sup in ledger.get("suppliers", []):
        gid = stable_id("vendor", sup["id"])
        if gid in sow.golden:
            continue
        sow.golden[gid] = GoldenRecord(
            id=gid,
            kind="vendor",
            source=source,
            data=sup,
            raw_ref=sup["id"],
        )
        n += 1

    for row in ledger.get("cash_history_90d", [])[-30:]:
        gid = stable_id("bank", source, row["date"], str(row["balance_cents"]))
        if gid in sow.golden:
            continue
        sow.golden[gid] = GoldenRecord(
            id=gid,
            kind="bank_transaction",
            source=source,
            data={
                "txn_date": row["date"],
                "inflow_cents": row["inflow_cents"],
                "outflow_cents": row["outflow_cents"],
                "balance_cents": row["balance_cents"],
                "memo": f"DAY CLOSE {row['date']}",
            },
            raw_ref=f"cash-{row['date']}",
        )
        n += 1

    # Seed messy demo bank wires (short pays, duplicates) — the Hyphenate corner
    messy = ledger.get("messy_events", [])
    for ev in messy:
        gid = stable_id("bank", ev["id"])
        if gid in sow.golden:
            continue
        sow.golden[gid] = GoldenRecord(
            id=gid,
            kind="bank_transaction",
            source=ev.get("source", "jpm"),
            data=ev,
            raw_ref=ev["id"],
        )
        # Open a work item per bank line (sync creates)
        sow.create_work(
            SYNC,
            kind=ev.get("work_kind", "cash_match"),
            subject=ev["id"],
            title=ev.get("title", ev.get("memo", "Bank line")),
            amount_cents=int(ev.get("amount_cents", 0)),
            evidence=[gid],
            payload={"bank": ev},
        )
        n += 1

    sow.cash_balance_cents = int(ledger.get("cash_balance_cents", sow.cash_balance_cents))
    sow.daily_burn_cents = int(ledger.get("daily_burn_cents", sow.daily_burn_cents))
    sow.sync_cursors[cursor_key] = now_iso()
    sow.audit.append(
        actor=SYNC.id,
        action="sync",
        subject=source,
        allowed=True,
        reason=f"synced {n} golden rows (cursor {prev} → {sow.sync_cursors[cursor_key]})",
        diff={"golden_added": {"from": 0, "to": n}},
    )
    return n


def default_ledger_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "seed" / "bakery_ledger.json"