"""
01 · SELF-LEARNING, at onboarding.

Learn the job from the company's history — not from a prompt dump.
Queries golden records, finds how short wires / duplicates were handled,
drafts a policy that needs human approval.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from sow.models import AI_RISK, Policy, new_id
from sow.store import SystemOfWork


class PolicyLearner:
    def __init__(self, sow: SystemOfWork) -> None:
        self.sow = sow

    def learn_short_wire_policy(self) -> Policy | None:
        """
        Hyphenate workshop example: wires ≤ $50 short → book to bank fees.
        We scan historical bank gaps in golden + precedents.
        """
        gaps: list[tuple[str, int]] = []
        for g in self.sow.golden.values():
            if g.kind != "bank_transaction":
                continue
            data = g.data
            gap = data.get("gap_cents")
            if gap is None:
                inv = data.get("invoice_amount_cents")
                paid = data.get("amount_cents")
                if inv is not None and paid is not None:
                    gap = int(inv) - int(paid)
            if gap is not None and 0 < int(gap) <= 5000:  # ≤ $50
                gaps.append((g.id, int(gap)))

        # Also count seeded historical short-wire precedents
        hist = self.sow.search_precedents(kind="short_wire")
        for p in hist:
            gap = int(p.correction.get("gap_cents", 0))
            if 0 < gap <= 5000:
                gaps.append((p.id, gap))

        if len(gaps) < 3:
            return None

        policy = Policy(
            id="pol-001",
            version=1,
            title="Short wire tolerance",
            rule="wire ≤ $50 short → book gap to 6850 Bank Fees",
            condition={"gap_cents_max": 5000, "direction": "short"},
            action={"gl_account": "6850", "label": "Bank Fees"},
            evidence=[g[0] for g in gaps[:20]],
            proposed_by=AI_RISK.id,
        )
        return self.sow.propose_policy(AI_RISK, policy)

    def learn_duplicate_invoice_policy(self) -> Policy | None:
        """amount + bank fingerprint + due date hash → block."""
        paid_hashes = [
            g.data.get("content_hash")
            for g in self.sow.golden.values()
            if g.kind == "invoice" and g.data.get("status") == "paid" and g.data.get("content_hash")
        ]
        if not paid_hashes:
            return None

        policy = Policy(
            id="pol-002",
            version=1,
            title="Duplicate AP invoice",
            rule="incoming invoice content_hash matching a paid invoice → BLOCK",
            condition={"match": "content_hash", "against_status": "paid"},
            action={"state": "BLOCKED", "notify": "owner"},
            evidence=paid_hashes[:10],
            proposed_by=AI_RISK.id,
        )
        return self.sow.propose_policy(AI_RISK, policy)

    def learn_autonomy_ceiling(self) -> Policy:
        """Cashier autonomy — coded limit, not prompt hope."""
        policy = Policy(
            id="pol-003",
            version=1,
            title="Cashier autonomy ceiling",
            rule="payments ≤ $1,000 auto-propose for gateway; above → HOLD for owner",
            condition={"amount_cents_max": 100_000},
            action={"below": "propose_pay", "above": "hold"},
            evidence=["governance"],
            proposed_by=AI_RISK.id,
        )
        # Auto-active for demo governance (owner can still revoke)
        p = self.sow.propose_policy(AI_RISK, policy)
        # In product, controller approves; for bakery one-person, Maya will approve policies in onboarding
        return p

    def onboard_from_history(self) -> list[Policy]:
        drafted: list[Policy] = []
        for fn in (
            self.learn_short_wire_policy,
            self.learn_duplicate_invoice_policy,
            self.learn_autonomy_ceiling,
        ):
            p = fn()
            if p:
                drafted.append(p)
        return drafted

    def match_policy(self, *, kind: str, context: dict[str, Any]) -> Policy | None:
        for p in self.sow.active_policies():
            if kind == "short_wire" and p.id.startswith("pol-001"):
                gap = int(context.get("gap_cents", 0))
                if 0 < gap <= int(p.condition.get("gap_cents_max", 0)):
                    return p
            if kind == "duplicate" and p.id.startswith("pol-002"):
                if context.get("content_hash") in {
                    g.data.get("content_hash")
                    for g in self.sow.golden.values()
                    if g.kind == "invoice" and g.data.get("status") == "paid"
                }:
                    return p
            if kind == "autonomy" and p.id.startswith("pol-003"):
                return p
        return None


def seed_historical_short_wires(sow: SystemOfWork) -> None:
    """Pretend a year of short wires already lived in the bakery's books."""
    from sow.models import Precedent

    for i, gap in enumerate([1200, 2500, 4800, 900, 3200, 1500, 4100], start=1):
        sow.add_precedent(
            Precedent(
                id=new_id("prec"),
                kind="short_wire",
                summary=f"Historical short wire gap ${gap/100:.2f} booked to 6850",
                subject=f"HIST-WIRE-{i:03d}",
                correction={"gap_cents": gap, "gl_account": "6850"},
                tags=["short_wire", "bank_fees"],
                created_by="onboarding",
            )
        )