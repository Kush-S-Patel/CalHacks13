"""
02 · SELF-IMPROVING, every day.

Every human correction becomes precedent. Agents search alike cases,
spot patterns, and propose a general policy — knowledge compounds
instead of walking out when the accountant leaves.
"""

from __future__ import annotations

from sow.models import AI_RISK, MAYA, Policy, Precedent, new_id
from sow.store import SystemOfWork


def apply_correction(
    sow: SystemOfWork,
    *,
    work_item_id: str,
    actor_id: str = MAYA.id,
    summary: str,
    correction: dict,
    tags: list[str],
) -> Precedent:
    """Human corrects an agent match → durable precedent."""
    item = sow.work_items[work_item_id]
    prec = Precedent(
        id=new_id("prec"),
        kind=item.kind,
        summary=summary,
        subject=item.subject,
        correction=correction,
        tags=tags,
        created_by=actor_id,
    )
    sow.add_precedent(prec)
    item.payload["corrected"] = correction
    item.payload["precedent_id"] = prec.id
    return prec


def maybe_generalize_split_wires(sow: SystemOfWork) -> Policy | None:
    """
    Workshop pol-014: one wire, many invoices → split when memo lists them
    and amounts add up. Triggered after ≥3 alike corrections.
    """
    alike = sow.search_precedents(tag="split_wire")
    if len(alike) < 3:
        return None
    if any(p.id == "pol-014" for p in sow.policies.values()):
        return None

    policy = Policy(
        id="pol-014",
        version=1,
        title="Split wire across invoices",
        rule="one wire, many invoice numbers in memo → split when amounts add up",
        condition={"memo_has_invoice_ids": True, "amounts_sum_equals_wire": True},
        action={"split": True},
        evidence=[p.id for p in alike],
        proposed_by=AI_RISK.id,
    )
    return sow.propose_policy(AI_RISK, policy)


def handle_rejection(
    sow: SystemOfWork,
    work_item_id: str,
    actor_id: str,
    reason: str,
) -> Precedent:
    """
    Handles a 'no' — strong Hyphenate signal.
    Rejection is not failure; it is learning fuel.
    """
    item = sow.reject(work_item_id, sow_actor(actor_id), reason)
    return apply_correction(
        sow,
        work_item_id=item.id,
        actor_id=actor_id,
        summary=f"Rejected: {reason}",
        correction={"rejected": True, "reason": reason},
        tags=["rejection", item.kind],
    )


def sow_actor(actor_id: str):
    from sow.models import ACTORS

    return ACTORS[actor_id]