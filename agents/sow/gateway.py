"""
Gateway — the one door. Every write to systems of record is checked.

Agents propose. Humans approve. Only the gateway posts.
This is how outcome-based pricing proves every outcome.
"""

from __future__ import annotations

from typing import Any

from sow.audit import AuditLog
from sow.models import GATEWAY, WorkItem
from sow.roles import Denied
from sow.transitions import transition


class Gateway:
    def __init__(self, audit: AuditLog) -> None:
        self.audit = audit
        self.posted: list[dict[str, Any]] = []  # stands in for NetSuite / bank / Stripe

    def post(self, item: WorkItem, *, destination: str = "ledger") -> dict[str, Any]:
        """Post an APPROVED (or BLOCKED) work item into the system of record."""
        if item.state not in ("APPROVED", "BLOCKED"):
            raise Denied(GATEWAY.id, "post", item.id, f"cannot post from state {item.state}")

        transition(
            item,
            "post",
            GATEWAY,
            self.audit,
            reason=f"gateway post → {destination}",
            patch={"payload": {"posted_to": destination}},
        )

        record = {
            "work_item_id": item.id,
            "kind": item.kind,
            "subject": item.subject,
            "amount_cents": item.amount_cents,
            "destination": destination,
            "policy_id": item.policy_id,
            "evidence": item.evidence,
            "payload": item.payload,
        }
        self.posted.append(record)
        return record