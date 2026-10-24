"""In-memory System of Work — shared by agents, humans, and the API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sow.audit import AuditLog
from sow.gateway import Gateway
from sow.models import (
    Actor,
    GoldenRecord,
    Policy,
    Precedent,
    WorkItem,
    WorkKind,
    new_id,
    now_iso,
)
from sow.roles import Denied, can
from sow.transitions import transition


class SystemOfWork:
    def __init__(self, room_id: str = "maya-bakery") -> None:
        self.room_id = room_id
        self.audit = AuditLog()
        self.gateway = Gateway(self.audit)
        self.work_items: dict[str, WorkItem] = {}
        self.policies: dict[str, Policy] = {}
        self.precedents: dict[str, Precedent] = {}
        self.golden: dict[str, GoldenRecord] = {}
        self.cash_balance_cents = 1_840_000
        self.daily_burn_cents = 165_000
        self.sync_cursors: dict[str, str] = {}

    # ── runway (FP&A surface) ─────────────────────────────────────────────

    @property
    def runway_days(self) -> float:
        if self.daily_burn_cents <= 0:
            return 999.0
        return self.cash_balance_cents / self.daily_burn_cents

    # ── Create (sync / agents) ────────────────────────────────────────────

    def create_work(
        self,
        actor: Actor,
        *,
        kind: WorkKind,
        subject: str,
        title: str,
        amount_cents: int = 0,
        evidence: list[str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> WorkItem:
        # Sync (and demo bootstrap) opens work items; agents then propose/ask/hold.
        if actor.role != "sync":
            ok, why = can(actor, "create", "work_item")
            if not ok:
                self.audit.append(
                    actor=actor.id,
                    action="create",
                    subject=subject,
                    allowed=False,
                    reason=why,
                    diff={},
                )
                raise Denied(actor.id, "create", subject, why)

        item = WorkItem(
            id=new_id("wi"),
            kind=kind,
            state="NEW",
            subject=subject,
            title=title,
            room_id=self.room_id,
            amount_cents=amount_cents,
            evidence=evidence or [],
            payload=payload or {},
        )
        self.work_items[item.id] = item
        self.audit.append(
            actor=actor.id,
            action="create",
            subject=item.id,
            allowed=True,
            reason=f"opened {kind} for {subject}",
            diff={"state": {"from": None, "to": "NEW"}},
            evidence=item.evidence,
        )
        return item

    def propose(self, item_id: str, actor: Actor, *, patch: dict[str, Any], reason: str) -> WorkItem:
        item = self.work_items[item_id]
        return transition(item, "propose", actor, self.audit, patch=patch, reason=reason)

    def ask(self, item_id: str, actor: Actor, question: str) -> WorkItem:
        item = self.work_items[item_id]
        return transition(
            item,
            "ask",
            actor,
            self.audit,
            patch={"question": question},
            reason=question,
        )

    def answer(self, item_id: str, actor: Actor, answer: str) -> WorkItem:
        item = self.work_items[item_id]
        return transition(
            item,
            "answer",
            actor,
            self.audit,
            patch={"answer": answer},
            reason=answer,
        )

    def approve(self, item_id: str, actor: Actor, reason: str = "owner approved") -> WorkItem:
        item = self.work_items[item_id]
        return transition(item, "approve", actor, self.audit, reason=reason)

    def reject(self, item_id: str, actor: Actor, reason: str) -> WorkItem:
        item = self.work_items[item_id]
        return transition(item, "reject", actor, self.audit, reason=reason)

    def block(self, item_id: str, actor: Actor, reason: str, *, patch: dict[str, Any] | None = None) -> WorkItem:
        item = self.work_items[item_id]
        return transition(item, "block", actor, self.audit, patch=patch, reason=reason)

    def hold(self, item_id: str, actor: Actor, reason: str) -> WorkItem:
        item = self.work_items[item_id]
        return transition(item, "hold", actor, self.audit, reason=reason)

    def post(self, item_id: str, destination: str = "ledger") -> dict[str, Any]:
        item = self.work_items[item_id]
        result = self.gateway.post(item, destination=destination)
        # Apply cash effects for posted payments / collections / defers
        self._apply_cash_effect(item)
        return result

    def _apply_cash_effect(self, item: WorkItem) -> None:
        kind = item.kind
        amt = item.amount_cents
        if kind == "spend_hold" and item.state == "POSTED":
            self.cash_balance_cents -= amt
        elif kind == "ar_collect" and item.payload.get("collected"):
            self.cash_balance_cents += amt
        elif kind == "forecast" and item.payload.get("defer_cents"):
            self.cash_balance_cents += int(item.payload["defer_cents"])
        elif kind == "ap_invoice" and item.state == "POSTED" and item.payload.get("blocked"):
            # blocked duplicate — cash preserved (not paid)
            pass
        elif kind == "ap_invoice" and item.payload.get("pay_cents"):
            self.cash_balance_cents -= int(item.payload["pay_cents"])

    # ── Policies & precedents (TIME) ──────────────────────────────────────

    def propose_policy(self, actor: Actor, policy: Policy) -> Policy:
        ok, why = can(actor, "propose", "policy")
        if not ok:
            self.audit.append(
                actor=actor.id,
                action="propose_policy",
                subject=policy.id,
                allowed=False,
                reason=why,
                diff={},
            )
            raise Denied(actor.id, "propose", policy.id, why)
        policy.proposed_by = actor.id
        policy.status = "needs_approval"
        self.policies[policy.id] = policy
        self.audit.append(
            actor=actor.id,
            action="propose_policy",
            subject=policy.id,
            allowed=True,
            reason=policy.rule,
            diff={"status": {"from": None, "to": "needs_approval"}},
            evidence=policy.evidence,
        )
        return policy

    def approve_policy(self, policy_id: str, actor: Actor) -> Policy:
        policy = self.policies[policy_id]
        ok, why = can(actor, "approve", "policy", proposed_by=policy.proposed_by)
        if not ok:
            self.audit.append(
                actor=actor.id,
                action="approve_policy",
                subject=policy_id,
                allowed=False,
                reason=why,
                diff={},
            )
            raise Denied(actor.id, "approve", policy_id, why)
        before = policy.status
        policy.status = "active"
        policy.approved_by = actor.id
        self.audit.append(
            actor=actor.id,
            action="approve_policy",
            subject=policy_id,
            allowed=True,
            reason="policy activated",
            diff={"status": {"from": before, "to": "active"}},
            evidence=policy.evidence,
        )
        return policy

    def add_precedent(self, precedent: Precedent) -> Precedent:
        self.precedents[precedent.id] = precedent
        self.audit.append(
            actor=precedent.created_by or "system",
            action="create_precedent",
            subject=precedent.id,
            allowed=True,
            reason=precedent.summary,
            diff={},
            evidence=[precedent.subject],
        )
        return precedent

    def search_precedents(self, *, kind: str | None = None, tag: str | None = None) -> list[Precedent]:
        out = list(self.precedents.values())
        if kind:
            out = [p for p in out if p.kind == kind]
        if tag:
            out = [p for p in out if tag in p.tags]
        return out

    def active_policies(self) -> list[Policy]:
        return [p for p in self.policies.values() if p.status == "active"]

    # ── Snapshot for UI / agents ──────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        return {
            "room_id": self.room_id,
            "cash_balance_cents": self.cash_balance_cents,
            "daily_burn_cents": self.daily_burn_cents,
            "runway_days": round(self.runway_days, 2),
            "work_items": [w.to_dict() for w in self.work_items.values()],
            "policies": [p.to_dict() for p in self.policies.values()],
            "precedents": [p.to_dict() for p in self.precedents.values()],
            "golden_count": len(self.golden),
            "audit_len": len(self.audit),
            "gateway_posted": list(self.gateway.posted),
            "open_holds": [
                w.to_dict() for w in self.work_items.values() if w.state == "HELD"
            ],
            "needs_info": [
                w.to_dict() for w in self.work_items.values() if w.state == "NEEDS_INFO"
            ],
        }

    def export(self, path: Path) -> None:
        path.write_text(json.dumps(self.snapshot() | {"audit": self.audit.all()}, indent=2), encoding="utf-8")


# Process-wide demo world (API + sim share this when imported carefully)
WORLD = SystemOfWork()