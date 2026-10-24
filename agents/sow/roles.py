"""
BUILD 2 — Agents and humans as one team.

Map who may do what, to which record. Limits are enforced in code,
not in the prompt. Separation of duties: proposer cannot approve own work.
Only the gateway may post to systems of record.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sow.models import Actor, ResourceKind

# role -> resource kind -> allowed actions
ROLES: dict[str, dict[str, set[str]]] = {
    "sync": {
        "work_item": {"create"},
    },
    # Swarm agents — propose / ask / read; never approve own work; never post
    "ai_risk": {
        "work_item": {"propose", "ask", "block"},
        "policy": {"propose"},
        "precedent": {"read", "create"},
    },
    "ai_procurement": {
        "work_item": {"propose", "ask", "counter"},
        "policy": {"propose"},
        "precedent": {"read"},
    },
    "ai_collections": {
        "work_item": {"propose", "ask", "chase"},
        "policy": {"propose"},
        "precedent": {"read"},
    },
    "ai_cashier": {
        "work_item": {"propose", "hold"},
        "precedent": {"read"},
    },
    "ai_cfo": {
        "work_item": {"propose", "ask", "arbitrate", "defer"},
        "policy": {"propose"},
        "precedent": {"read", "create"},
        "forecast": {"update"},
    },
    # Humans
    "human_owner": {  # Maya — one-person company controller
        "work_item": {"approve", "reject", "answer"},
        "policy": {"approve", "reject"},
        "forecast": {"read"},
    },
    "human_accountant": {
        "work_item": {"approve", "reject", "answer", "correct"},
        "policy": {"propose"},
        "precedent": {"create"},
    },
    "human_controller": {
        "policy": {"approve", "reject"},
        "work_item": {"approve", "reject"},
    },
    # Gateway alone writes systems of record
    "gateway": {
        "work_item": {"post"},
        "ledger": {"post"},
        "bank": {"post"},
    },
}


class Denied(PermissionError):
    """Raised when can() fails — always logged to audit."""

    def __init__(self, actor_id: str, action: str, resource_id: str, why: str):
        self.actor_id = actor_id
        self.action = action
        self.resource_id = resource_id
        self.why = why
        super().__init__(f"DENIED {actor_id} {action} {resource_id}: {why}")


def can(actor: Actor, action: str, resource_kind: ResourceKind, *, proposed_by: str | None = None) -> tuple[bool, str]:
    """
    Return (allowed, reason). Separation of duties: cannot approve what you proposed.
    """
    allowed = ROLES.get(actor.role, {}).get(resource_kind, set())
    if action not in allowed:
        return False, f"role {actor.role} cannot {action} on {resource_kind}"

    if action == "approve" and proposed_by and proposed_by == actor.id:
        return False, "separation of duties: proposer cannot approve own work"

    if action == "post" and actor.role != "gateway":
        return False, "only gateway may post to systems of record"

    return True, "ok"