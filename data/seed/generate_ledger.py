#!/usr/bin/env python3
"""
Frozen bakery ledger + messy corner events for Hyphenate Build 1.

Systems of record (raw) → sync → golden. Includes short wires, duplicate AP,
late AR, and the autonomy-hold deposit — the answer key for the demo.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

RNG = random.Random(13)
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


def _supply_chain() -> dict:
    """Full upstream → downstream chain with monthly dollar volumes."""
    return {
        "nodes": [
            {"id": "farm-wheat", "name": "Sacramento Wheat Co-op", "kind": "origin", "tier": 0, "tier_label": "Origin", "monthly_cents": 4_800_000},
            {"id": "farm-dairy", "name": "Petaluma Dairy Farms", "kind": "origin", "tier": 0, "tier_label": "Origin", "monthly_cents": 3_600_000},
            {"id": "mill-coastal", "name": "Coastal Grain Mill", "kind": "processor", "tier": 1, "tier_label": "Processor", "monthly_cents": 5_200_000},
            {"id": "sup-flour-co", "name": "North Bay Flour Co", "kind": "distributor", "tier": 2, "tier_label": "Distributor", "monthly_cents": 1_820_000},
            {"id": "sup-alt-flour", "name": "Coastal Grain Alt", "kind": "distributor", "tier": 2, "tier_label": "Distributor", "monthly_cents": 1_480_000},
            {"id": "sup-dairy", "name": "Valley Dairy", "kind": "distributor", "tier": 2, "tier_label": "Distributor", "monthly_cents": 1_240_000},
            {"id": "sup-packaging", "name": "ClearWrap Packaging", "kind": "packaging", "tier": 2, "tier_label": "Packaging", "monthly_cents": 420_000},
            {"id": "plant-ink", "name": "EcoInk Labels", "kind": "packaging", "tier": 2, "tier_label": "Packaging", "monthly_cents": 98_000},
            {"id": "cold-chain", "name": "Bay Cold Logistics", "kind": "logistics", "tier": 3, "tier_label": "Logistics", "monthly_cents": 360_000},
            {"id": "maya-bakery", "name": "Maya's Bakery (HQ)", "kind": "company", "tier": 4, "tier_label": "Production", "monthly_cents": 6_200_000},
            {"id": "site-mission", "name": "Mission Pop-up", "kind": "site", "tier": 5, "tier_label": "Channels", "monthly_cents": 1_420_000},
            {"id": "site-oakland", "name": "Oakland Kitchen", "kind": "site", "tier": 5, "tier_label": "Channels", "monthly_cents": 2_280_000},
            {"id": "cust-wholesale", "name": "Bay Area Wholesale", "kind": "customer", "tier": 6, "tier_label": "Wholesale", "monthly_cents": 2_850_000},
            {"id": "cust-harbor", "name": "Harbor Cafe Group", "kind": "customer", "tier": 6, "tier_label": "Foodservice", "monthly_cents": 920_000},
            {"id": "cust-summit", "name": "Summit Grocery", "kind": "customer", "tier": 6, "tier_label": "Retail", "monthly_cents": 1_140_000},
            {"id": "cust-oak", "name": "Oak Street Market", "kind": "customer", "tier": 6, "tier_label": "Retail", "monthly_cents": 680_000},
        ],
        "edges": [
            {"from": "farm-wheat", "to": "mill-coastal", "amount_cents": 4_800_000, "label": "wheat $48,000", "kind": "goods"},
            {"from": "mill-coastal", "to": "sup-flour-co", "amount_cents": 2_840_000, "label": "flour $28,400", "kind": "goods"},
            {"from": "mill-coastal", "to": "sup-alt-flour", "amount_cents": 2_210_000, "label": "flour $22,100", "kind": "goods"},
            {"from": "farm-dairy", "to": "sup-dairy", "amount_cents": 3_600_000, "label": "milk $36,000", "kind": "goods"},
            {"from": "sup-flour-co", "to": "maya-bakery", "amount_cents": 1_820_000, "label": "AP $18,200/mo", "kind": "goods"},
            {"from": "sup-alt-flour", "to": "maya-bakery", "amount_cents": 0, "label": "alt (trial)", "kind": "goods"},
            {"from": "sup-dairy", "to": "maya-bakery", "amount_cents": 1_240_000, "label": "AP $12,400/mo", "kind": "goods"},
            {"from": "sup-packaging", "to": "maya-bakery", "amount_cents": 420_000, "label": "AP $4,200/mo", "kind": "goods"},
            {"from": "plant-ink", "to": "sup-packaging", "amount_cents": 98_000, "label": "labels $980", "kind": "goods"},
            {"from": "cold-chain", "to": "maya-bakery", "amount_cents": 360_000, "label": "freight $3,600", "kind": "logistics"},
            {"from": "maya-bakery", "to": "site-mission", "amount_cents": 1_420_000, "label": "transfer $14,200", "kind": "internal"},
            {"from": "maya-bakery", "to": "site-oakland", "amount_cents": 2_280_000, "label": "transfer $22,800", "kind": "internal"},
            {"from": "maya-bakery", "to": "cust-wholesale", "amount_cents": 2_850_000, "label": "rev $28,500", "kind": "revenue"},
            {"from": "site-oakland", "to": "cust-harbor", "amount_cents": 920_000, "label": "rev $9,200", "kind": "revenue"},
            {"from": "site-mission", "to": "cust-summit", "amount_cents": 1_140_000, "label": "rev $11,400", "kind": "revenue"},
            {"from": "site-mission", "to": "cust-oak", "amount_cents": 680_000, "label": "rev $6,800", "kind": "revenue"},
            {
                "id": "inv-dup-incoming",
                "from": "sup-flour-co",
                "to": "maya-bakery",
                "amount_cents": 420_000,
                "label": "DUP $4,200",
                "kind": "payment",
                "fraud": True,
            },
        ],
    }


def _money_graph() -> dict:
    return {
        "nodes": [
            {"id": "maya-bakery", "name": "Maya's Bakery", "kind": "company", "amount_cents": 1_840_000},
            {"id": "sup-flour-co", "name": "North Bay Flour", "kind": "vendor", "amount_cents": 1_820_000},
            {"id": "sup-dairy", "name": "Valley Dairy", "kind": "vendor", "amount_cents": 1_240_000},
            {
                "id": "inv-dup-incoming",
                "name": "INV dup $4,200",
                "kind": "invoice",
                "amount_cents": 420_000,
                "fraud": True,
                "aliases": ["inv-dup-original"],
            },
            {"id": "inv-dup-original", "name": "INV paid $4,200", "kind": "invoice", "amount_cents": 420_000},
            {"id": "JPM-88310442", "name": "Wire $57,975", "kind": "bank_txn", "amount_cents": 5_797_500},
            {"id": "ar-big-cafe", "name": "AR Harbor $9,200", "kind": "receivable", "amount_cents": 920_000},
            {
                "id": "appr-supplier-deposit",
                "name": "Deposit $1,400",
                "kind": "payment",
                "amount_cents": 140_000,
                "held": True,
            },
        ],
        "edges": [
            {"from": "maya-bakery", "to": "sup-flour-co", "amount_cents": 1_820_000, "kind": "payment", "label": "$18,200/mo"},
            {"from": "maya-bakery", "to": "sup-dairy", "amount_cents": 1_240_000, "kind": "payment", "label": "$12,400/mo"},
            {
                "id": "inv-dup-incoming",
                "from": "sup-flour-co",
                "to": "maya-bakery",
                "amount_cents": 420_000,
                "kind": "invoice",
                "fraud": True,
                "invoice_id": "inv-dup-incoming",
                "label": "FRAUD $4,200",
            },
            {"from": "inv-dup-original", "to": "sup-flour-co", "amount_cents": 420_000, "kind": "paid", "label": "paid $4,200"},
            {"from": "JPM-88310442", "to": "maya-bakery", "amount_cents": 5_797_500, "kind": "wire", "label": "$57,975 (-$25)"},
            {"from": "ar-big-cafe", "to": "maya-bakery", "amount_cents": 920_000, "kind": "ar", "label": "$9,200 late"},
            {
                "from": "maya-bakery",
                "to": "appr-supplier-deposit",
                "amount_cents": 140_000,
                "kind": "hold",
                "held": True,
                "label": "HOLD $1,400",
            },
        ],
    }


def main() -> None:
    today = date(2026, 10, 23)
    invoices = []
    for i in range(30):
        sup = SUPPLIERS[i % 3]
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

    # Paid twin for duplicate detection demo
    invoices.append(
        {
            "id": "inv-dup-original",
            "vendor_id": "sup-flour-co",
            "vendor_name": "North Bay Flour Co",
            "amount_cents": 420_000,
            "bank_fingerprint": "bank-nbflour-001",
            "due_date_iso": "2026-10-25",
            "status": "paid",
            "content_hash": "420000|bank-nbflour-001|2026-10-25",
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
    cash_history[-1]["balance_cents"] = 1_840_000

    # Messy corner — Hyphenate: one economic event touches many systems
    messy_events = [
        {
            "id": "JPM-88310442",
            "source": "jpm",
            "work_kind": "cash_match",
            "title": "Wire in Harbor Cafe $57,975 vs INV $58,000 ($25 short)",
            "memo": "WIRE IN HARBOR CAFE INV-AR-091",
            "amount_cents": 5_797_500,
            "invoice_amount_cents": 5_800_000,
            "gap_cents": 2500,
            "customer": "Harbor Cafe Group",
        },
        {
            "id": "JPM-SPLIT-5602",
            "source": "jpm",
            "work_kind": "cash_match",
            "title": "One wire covering INV-1077 + INV-1078",
            "memo": "WIRE IN ACME INV-1077 INV-1078",
            "amount_cents": 12_000_00,
            "split_candidates": ["INV-1077", "INV-1078"],
        },
    ]

    ledger = {
        "room_id": "maya-bakery",
        "owner": "Maya",
        "business": "Maya's Bakery",
        "as_of": today.isoformat(),
        "systems_of_record": ["jpm_bank", "manual_ap", "stripe_test", "crm_sheet"],
        "cash_balance_cents": 1_840_000,
        "daily_burn_cents": 165_000,
        "runway_days": round(18400 / 1650, 2),
        "suppliers": SUPPLIERS,
        "invoices": invoices,
        "cash_history_90d": cash_history,
        "messy_events": messy_events,
        "customers": [
            {"id": "cust-harbor", "name": "Harbor Cafe Group", "ar_cents": 920_000},
            {"id": "cust-summit", "name": "Summit Grocery", "ar_cents": 480_000},
            {"id": "cust-oak", "name": "Oak Street Market", "ar_cents": 215_000},
            {"id": "cust-wholesale", "name": "Bay Area Wholesale", "ar_cents": 1_240_000},
        ],
        "supply_chain": _supply_chain(),
        "money_graph": _money_graph(),
        "gl_accounts": {
            "6850": "Bank Fees",
            "1000": "Operating Cash",
            "2000": "Accounts Payable",
            "1100": "Accounts Receivable",
        },
        "demo_chaos": {
            "price_spike": {"supplier_id": "sup-flour-co", "pct": 40},
            "duplicate_invoice": {
                "amount_cents": 420_000,
                "content_hash": "420000|bank-nbflour-001|2026-10-25",
            },
            "late_ar": {
                "id": "ar-big-cafe",
                "customer": "Harbor Cafe Group",
                "amount_cents": 920_000,
                "days_late": 12,
            },
            "hold_payment": {"amount_cents": 140_000, "id": "appr-supplier-deposit"},
            "defer_spend_cents": 380_000,
        },
        "answer_key": {
            "corner": "Cash match + AP fraud + AR + spend governance",
            "pol_001": "wire ≤ $50 short → 6850 Bank Fees",
            "pol_002": "duplicate content_hash → BLOCK",
            "pol_003": "pay ≤ $1000 autonomy; else HOLD",
        },
    }

    OUT.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(invoices)} invoices, {len(messy_events)} messy events)")


if __name__ == "__main__":
    main()