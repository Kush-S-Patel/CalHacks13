#!/usr/bin/env python3
"""
SwarmCFO deterministic offline simulation.

The exact judge chaos scenario from the pitch. Runs without Wi-Fi / APIs.
Use as demo fallback and as the seed for live agent behavior.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOM = "maya-bakery"
CASH_START = 1_840_000  # cents
BURN = 165_000


@dataclass
class Action:
    agent: str
    action_type: str
    target_id: str
    rationale: str
    amount_cents: int = 0


@dataclass
class World:
    cash_cents: int = CASH_START
    burn_cents: int = BURN
    actions: list[Action] = field(default_factory=list)
    approvals: list[dict] = field(default_factory=list)

    @property
    def runway_days(self) -> float:
        return self.cash_cents / self.burn_cents if self.burn_cents else 999.0

    def log(self, action: Action) -> None:
        self.actions.append(action)
        print(
            f"  [{action.agent:12}] {action.action_type.upper():9} "
            f"{action.rationale}"
            + (f" (${action.amount_cents/100:,.0f})" if action.amount_cents else "")
        )


def inject_price_spike(w: World) -> None:
    print("\n▸ CHAOS: flour supplier +40%")
    time.sleep(0.15)
    w.log(
        Action(
            "procurement",
            "counter",
            "sup-flour-co→sup-alt-flour",
            "Counter-offer SENT to Coastal Grain Alt — ~$2,728/mo saved",
            272_800,
        )
    )
    w.log(
        Action(
            "risk",
            "flag",
            "sup-alt-flour",
            "Alt trust_score 0.70 — distrust until trial",
        )
    )
    w.log(
        Action(
            "cfo",
            "arbitrate",
            "sup-alt-flour",
            "Trial alt + watchlist (Procurement vs Risk)",
        )
    )


def inject_duplicate(w: World) -> None:
    print("\n▸ CHAOS: duplicate $4,200 invoice")
    time.sleep(0.15)
    w.log(
        Action(
            "risk",
            "block",
            "inv-dup-incoming",
            "Duplicate hash (amount+bank+date) — BLOCKED. Saved $4,200",
            420_000,
        )
    )


def inject_late_ar(w: World) -> None:
    print("\n▸ CHAOS: Harbor Cafe $9,200 / 12 days late")
    time.sleep(0.15)
    w.log(
        Action(
            "collections",
            "chase",
            "ar-big-cafe",
            "Firm chase + 2% early-pay incentive SENT",
            920_000,
        )
    )


def cfo_close(w: World) -> None:
    print("\n▸ CFO close-out")
    time.sleep(0.15)
    before = w.runway_days
    w.cash_cents += 380_000  # defer non-critical spend
    w.log(
        Action(
            "cfo",
            "defer",
            "noncritical-spend",
            "Defer $3,800 packaging refresh",
            380_000,
        )
    )
    w.log(
        Action(
            "cfo",
            "announce",
            "runway",
            f"Runway {before:.0f} → {w.runway_days:.0f} days",
        )
    )
    w.approvals.append(
        {
            "id": "appr-supplier-deposit",
            "description": "Supplier deposit — North Bay Flour Co",
            "amount_cents": 140_000,
            "status": "waiting",
        }
    )
    w.log(
        Action(
            "cashier",
            "hold",
            "appr-supplier-deposit",
            "$1,400 exceeds $1,000 autonomy — WAITING for Approve",
            140_000,
        )
    )


def owner_approve(w: World) -> None:
    print("\n▸ OWNER: one-tap Approve")
    time.sleep(0.15)
    appr = w.approvals[0]
    appr["status"] = "approved"
    w.cash_cents -= appr["amount_cents"]
    w.log(
        Action(
            "owner",
            "approve",
            appr["id"],
            "Every screen updates simultaneously",
            appr["amount_cents"],
        )
    )


def main() -> None:
    print("=" * 60)
    print(" SwarmCFO sim — Maya's Bakery")
    print(f" Cash ${CASH_START/100:,.0f} · burn ${BURN/100:,.0f}/day · runway ~{CASH_START/BURN:.0f} days")
    print("=" * 60)

    w = World()
    inject_price_spike(w)
    inject_duplicate(w)
    inject_late_ar(w)
    cfo_close(w)

    print(f"\n  RUNWAY NOW: {w.runway_days:.0f} days  |  WAITING: $1,400")
    owner_approve(w)
    print(f"\n  FINAL RUNWAY: {w.runway_days:.0f} days")
    print(f"  ACTIONS LOGGED: {len(w.actions)}")

    out = Path(__file__).resolve().parent / "last_sim.json"
    out.write_text(
        json.dumps(
            {
                "room": ROOM,
                "runway_days": w.runway_days,
                "cash_cents": w.cash_cents,
                "actions": [asdict(a) for a in w.actions],
                "approvals": w.approvals,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()