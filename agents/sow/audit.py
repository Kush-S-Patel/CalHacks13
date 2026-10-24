"""
BUILD 4 — Traceability.

Append-only. Fixes are new events. Denied attempts are logged too.
Months later, "why was INV-x closed short?" is one query.
"""

from __future__ import annotations

from typing import Any

from sow.models import AuditEvent, now_iso


class AuditLog:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(
        self,
        *,
        actor: str,
        action: str,
        subject: str,
        allowed: bool,
        reason: str,
        diff: dict[str, Any],
        evidence: list[str] | None = None,
    ) -> AuditEvent:
        ev = AuditEvent(
            at=now_iso(),
            actor=actor,
            action=action,
            subject=subject,
            allowed=allowed,
            reason=reason,
            diff=diff,
            evidence=evidence or [],
        )
        self._events.append(ev)
        return ev

    def for_subject(self, subject: str) -> list[dict[str, Any]]:
        """Answer 'why?' — the Hyphenate audit demo query."""
        return [e.to_dict() for e in self._events if e.subject == subject or subject in e.evidence]

    def all(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._events]

    def denials(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._events if not e.allowed]

    def __len__(self) -> int:
        return len(self._events)