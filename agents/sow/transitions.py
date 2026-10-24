"""
BUILD 3 — The harness meets the application.

Agent tools are CRUD on the work. Every change goes through transition().
D never: a reversal is a new transition. Denied attempts are logged too.
"""

from __future__ import annotations

from typing import Any

from sow.audit import AuditLog
from sow.models import Actor, WorkItem, WorkState, now_iso
from sow.roles import Denied, can

# (state, action) -> next state
TRANSITIONS: dict[tuple[WorkState, str], WorkState] = {
    ("NEW", "propose"): "PROPOSED",
    ("NEW", "block"): "BLOCKED",
    ("NEW", "hold"): "HELD",
    ("NEW", "ask"): "NEEDS_INFO",
    ("PROPOSED", "ask"): "NEEDS_INFO",
    ("PROPOSED", "approve"): "APPROVED",
    ("PROPOSED", "reject"): "REJECTED",
    ("PROPOSED", "block"): "BLOCKED",
    ("PROPOSED", "hold"): "HELD",
    ("PROPOSED", "arbitrate"): "PROPOSED",  # CFO decision stays proposed until approve
    ("NEEDS_INFO", "answer"): "PROPOSED",
    ("NEEDS_INFO", "arbitrate"): "PROPOSED",  # CFO can resolve an ask
    ("NEEDS_INFO", "reject"): "REJECTED",
    ("HELD", "approve"): "APPROVED",
    ("HELD", "reject"): "REJECTED",
    ("APPROVED", "post"): "POSTED",
    ("BLOCKED", "post"): "POSTED",  # post a block = write fraud flag to SoR via gateway
}


def _diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    keys = set(before) | set(after)
    for k in keys:
        if before.get(k) != after.get(k):
            out[k] = {"from": before.get(k), "to": after.get(k)}
    return out


def transition(
    item: WorkItem,
    action: str,
    actor: Actor,
    audit: AuditLog,
    *,
    patch: dict[str, Any] | None = None,
    reason: str = "",
) -> WorkItem:
    """
    Atomic state change + append-only audit event (same logical commit).
    Raises Denied when permissions or transition table reject the call.
    """
    before = item.snapshot()
    to = TRANSITIONS.get((item.state, action))
    ok_role, role_why = can(
        actor,
        action,
        "work_item",
        proposed_by=item.proposed_by,
    )
    ok = to is not None and ok_role
    why = reason or (role_why if not ok_role else f"{item.state} --{action}--> {to}")

    if ok and to is not None:
        if patch:
            for key, val in patch.items():
                if key == "payload" and isinstance(val, dict):
                    item.payload = {**item.payload, **val}
                elif hasattr(item, key) and key not in ("id", "state"):
                    setattr(item, key, val)
        item.state = to
        item.updated_at = now_iso()
        if action == "propose":
            item.proposed_by = actor.id
        if action == "approve":
            item.approved_by = actor.id
        if action == "ask" and patch and "question" in patch:
            item.question = patch["question"]
        if action == "answer" and patch and "answer" in patch:
            item.answer = patch["answer"]

    after = item.snapshot()
    audit.append(
        actor=actor.id,
        action=action,
        subject=item.id,
        allowed=ok,
        reason=why,
        diff=_diff(before, after) if ok else {},
        evidence=list(item.evidence),
    )

    if not ok:
        detail = role_why if not ok_role else f"no transition ({item.state}, {action})"
        raise Denied(actor.id, action, item.id, detail)

    return item