"""Durable storage for the governed Claims system-of-work artifacts.

Claim packages already persist as JSON.  The judged workflow also depends on
work items, policies, precedents, and audit receipts that used to live only in
process memory.  This small SQLite store keeps those artifacts restart-safe.
Audit rows are insert-only: an existing event ID is never updated.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

from sow.models import AuditEvent, Policy, Precedent, WorkItem
from sow.store import SystemOfWork


class GuidedPersistence:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else Path(
            os.getenv("SWARMCFO_GUIDED_DB")
            or str(Path(__file__).resolve().parents[2] / "data" / "erp_vault" / "guided_sow.sqlite3")
        )
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS guided_work_items (
                    id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL,
                    data_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_guided_work_claim
                    ON guided_work_items(claim_id);

                CREATE TABLE IF NOT EXISTS guided_policies (
                    id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL,
                    data_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_guided_policy_claim
                    ON guided_policies(claim_id);

                CREATE TABLE IF NOT EXISTS guided_precedents (
                    id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL,
                    data_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_guided_precedent_claim
                    ON guided_precedents(claim_id);

                CREATE TABLE IF NOT EXISTS guided_audit_events (
                    id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL,
                    at TEXT NOT NULL,
                    data_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_guided_audit_claim
                    ON guided_audit_events(claim_id, at);

                -- An audit receipt may cite more than one claim in its evidence.
                -- Keep the immutable event body once, then associate it with every
                -- claim whose audit query returns it.
                CREATE TABLE IF NOT EXISTS guided_audit_event_claims (
                    event_id TEXT NOT NULL,
                    claim_id TEXT NOT NULL,
                    PRIMARY KEY(event_id, claim_id),
                    FOREIGN KEY(event_id) REFERENCES guided_audit_events(id)
                );
                CREATE INDEX IF NOT EXISTS idx_guided_audit_event_claim
                    ON guided_audit_event_claims(claim_id, event_id);

                INSERT OR IGNORE INTO guided_audit_event_claims(event_id, claim_id)
                    SELECT id, claim_id FROM guided_audit_events;
                """
            )

    @staticmethod
    def _json(value: dict[str, Any]) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _artifact_ids(package: Any) -> tuple[set[str], str | None, str | None]:
        flow = (package.meta or {}).get("guided_flow") or {}
        work_ids = set(package.work_item_ids or [])
        work_ids.update(
            str(value)
            for value in (
                flow.get("prepare_work_item_id"),
                flow.get("question_work_item_id"),
                flow.get("future_claim_work_item_id"),
            )
            if value
        )
        return work_ids, flow.get("policy_id"), flow.get("precedent_id")

    def save_claim(self, sow: SystemOfWork, package: Any) -> None:
        """Upsert mutable artifacts and append new audit rows for one claim."""
        work_ids, policy_id, precedent_id = self._artifact_ids(package)
        audit_events = sow.audit.for_subject(package.id)
        with self._lock, self._connect() as connection:
            for work_id in sorted(work_ids):
                item = sow.work_items.get(work_id)
                if not item:
                    continue
                connection.execute(
                    """
                    INSERT INTO guided_work_items(id, claim_id, data_json)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        claim_id=excluded.claim_id,
                        data_json=excluded.data_json
                    """,
                    (item.id, package.id, self._json(item.to_dict())),
                )
            if policy_id and policy_id in sow.policies:
                policy = sow.policies[policy_id]
                connection.execute(
                    """
                    INSERT INTO guided_policies(id, claim_id, data_json)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        claim_id=excluded.claim_id,
                        data_json=excluded.data_json
                    """,
                    (policy.id, package.id, self._json(policy.to_dict())),
                )
            if precedent_id and precedent_id in sow.precedents:
                precedent = sow.precedents[precedent_id]
                connection.execute(
                    """
                    INSERT INTO guided_precedents(id, claim_id, data_json)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        claim_id=excluded.claim_id,
                        data_json=excluded.data_json
                    """,
                    (precedent.id, package.id, self._json(precedent.to_dict())),
                )
            for event in audit_events:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO guided_audit_events(id, claim_id, at, data_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (event["id"], package.id, event["at"], self._json(event)),
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO guided_audit_event_claims(event_id, claim_id)
                    VALUES (?, ?)
                    """,
                    (event["id"], package.id),
                )

    def restore_claim(self, sow: SystemOfWork, claim_id: str) -> dict[str, int]:
        """Merge one persisted claim's artifacts into a fresh SystemOfWork."""
        with self._lock, self._connect() as connection:
            work_rows = connection.execute(
                "SELECT data_json FROM guided_work_items WHERE claim_id = ?",
                (claim_id,),
            ).fetchall()
            policy_rows = connection.execute(
                "SELECT data_json FROM guided_policies WHERE claim_id = ?",
                (claim_id,),
            ).fetchall()
            precedent_rows = connection.execute(
                "SELECT data_json FROM guided_precedents WHERE claim_id = ?",
                (claim_id,),
            ).fetchall()
            audit_rows = connection.execute(
                """
                SELECT events.data_json
                FROM guided_audit_events AS events
                JOIN guided_audit_event_claims AS claims
                    ON claims.event_id = events.id
                WHERE claims.claim_id = ?
                ORDER BY events.at, events.id
                """,
                (claim_id,),
            ).fetchall()

        for row in work_rows:
            item = WorkItem(**json.loads(row["data_json"]))
            sow.work_items[item.id] = item
        for row in policy_rows:
            policy = Policy(**json.loads(row["data_json"]))
            sow.policies[policy.id] = policy
        for row in precedent_rows:
            precedent = Precedent(**json.loads(row["data_json"]))
            sow.precedents[precedent.id] = precedent
        restored_events = [AuditEvent(**json.loads(row["data_json"])) for row in audit_rows]
        sow.audit.restore(restored_events)
        return {
            "work_items": len(work_rows),
            "policies": len(policy_rows),
            "precedents": len(precedent_rows),
            "audit_events": len(audit_rows),
        }

    def restore_all(self, sow: SystemOfWork) -> dict[str, int]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT claim_id FROM guided_work_items
                UNION SELECT claim_id FROM guided_policies
                UNION SELECT claim_id FROM guided_precedents
                UNION SELECT claim_id FROM guided_audit_event_claims
                """
            ).fetchall()
        totals = {"claims": 0, "work_items": 0, "policies": 0, "precedents": 0, "audit_events": 0}
        for row in rows:
            counts = self.restore_claim(sow, str(row["claim_id"]))
            totals["claims"] += 1
            for key, value in counts.items():
                totals[key] += value
        return totals

    def audit_rows(self, claim_id: str) -> list[dict[str, Any]]:
        """Read persisted receipts for restart tests and the technical drawer."""
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT events.data_json
                FROM guided_audit_events AS events
                JOIN guided_audit_event_claims AS claims
                    ON claims.event_id = events.id
                WHERE claims.claim_id = ?
                ORDER BY events.at, events.id
                """,
                (claim_id,),
            ).fetchall()
        return [json.loads(row["data_json"]) for row in rows]

    def clear(self) -> None:
        """Clear only guided demo artifacts for an intentional application reset."""
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM guided_audit_event_claims")
            connection.execute("DELETE FROM guided_audit_events")
            connection.execute("DELETE FROM guided_precedents")
            connection.execute("DELETE FROM guided_policies")
            connection.execute("DELETE FROM guided_work_items")


GUIDED_PERSISTENCE = GuidedPersistence()
