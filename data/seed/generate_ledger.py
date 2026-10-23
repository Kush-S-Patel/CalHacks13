#!/usr/bin/env python3
"""Generate frozen bakery ledger: 30 invoices, 4 suppliers, 90 days cash history."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

RNG = random.Random(13)  # deterministic seed for CalHacks rehearsals
OUT = Path(__file__).with_name("bakery_ledger.json")

SUPPLIERS = [
    {
        "id": "sup-flour-co",
        "name": "North Bay Flour Co",
        "category": "flour",
        "unit_price_cents": 4200,
        "bank_fingerprint": "bank-nbflour-001",
        "trust_score": 0.92,
    },
    {
        "id": "sup-dairy",
        "name": "Valley Dairy",
        "category": "dairy",
        "unit_price_cents": 2850,
        "bank_fingerprint": "bank-valley-002",
        "trust_score": 0.88,
    },
    {
        "id": "sup-packaging",
        "name": "ClearWrap Packaging",
        "category": "packaging",
        "unit_price_cents": 1800,
        "bank_fingerprint": "bank-clearwrap-003",
        "trust_score": 0.75,
    },
    {
        "id": "sup-alt-flour",
        "name": "Coastal Grain Alt",
        "category": "flour",
        "unit_price_cents": 3800,
        "bank_fingerprint": "bank-coastal-004",
        "trust_score": 0.70,
    },
]


def main() -> None:
    today = date(2026, 10, 23)
    invoices = []
    for i in range(30):
        sup = SUPPLIERS[i % 3]  # exclude alt from historical
        d = today - timedelta(days=RNG.randint(1, 80))
        amount = RNG.randint(800, 6500) * 100
        invoices.append(
            {
                "id": f"inv-{i+1:03d}",
                "vendor_id": sup["id"],
                "vendor_name": sup["name"],
                "amount_cents": amount,
                "bank_fingerprint": sup["bank_fingerprint"],
                "due_date_iso": d.isoformat(),
                "status": RNG.choice(["paid", "paid", "paid", "open"]),
                "content_hash": f"{amount}|{sup['bank_fingerprint']}|{d.isoformat()}",
            }
        )

    cash_history = []
    bal = 2_200_000
    for day in range(90, 0, -1):
        d = today - timedelta(days=day)
        inflow = RNG.randint(800, 2800) * 100
        outflow = RNG.randint(1200, 2200) * 100
        bal += inflow - outflow
        cash_history.append(
            {
                "date": d.isoformat(),
                "inflow_cents": inflow,
                "outflow_cents": outflow,
                "balance_cents": bal,
            }
        )

    # Pin ending balance to pitch number
    cash_history[-1]["balance_cents"] = 1_840_000

    ledger = {
        "room_id": "maya-bakery",
        "owner": "Maya",
        "business": "Maya's Bakery",
        "as_of": today.isoformat(),
        "cash_balance_cents": 1_840_000,
        "daily_burn_cents": 165_000,
        "runway_days": round(18400 / 1650, 2),
        "suppliers": SUPPLIERS,
        "invoices": invoices,
        "cash_history_90d": cash_history,
        "demo_chaos": {
            "price_spike": {"supplier_id": "sup-flour-co", "pct": 40},
            "duplicate_invoice": {"amount_cents": 420_000, "twin_of": "seed"},
            "late_ar": {
                "id": "ar-big-cafe",
                "customer": "Harbor Cafe Group",
                "amount_cents": 920_000,
                "days_late": 12,
            },
            "hold_payment": {"amount_cents": 140_000, "id": "appr-supplier-deposit"},
            "defer_spend_cents": 380_000,
        },
    }

    OUT.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(invoices)} invoices, {len(cash_history)} cash days)")


if __name__ == "__main__":
    main()