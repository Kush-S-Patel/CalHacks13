"""
Context / relationship / supply-chain graphs for the demo.

Nodes carry exact dollar amounts. Fraudulent edges and nodes are flagged
from System of Work state (blocked AP, denied posts, duplicate hashes).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sow.store import SystemOfWork
from sow.sync import default_ledger_path, load_raw_ledger


def _usd(cents: int | float) -> str:
    return f"${cents / 100:,.2f}" if abs(cents) % 100 else f"${cents / 100:,.0f}"


def build_graphs(sow: SystemOfWork, ledger: dict[str, Any] | None = None) -> dict[str, Any]:
    if ledger is None:
        path = default_ledger_path()
        ledger = load_raw_ledger(path) if path.exists() else {}

    chain = ledger.get("supply_chain") or _default_supply_chain()
    money = ledger.get("money_graph") or _default_money_graph()

    # Live fraud overlays from SoW
    fraud_subjects: set[str] = set()
    fraud_amounts: dict[str, int] = {}
    for w in sow.work_items.values():
        blocked = w.state == "BLOCKED" or bool(w.payload.get("blocked"))
        if blocked or (w.kind == "ap_invoice" and "dup" in w.subject):
            fraud_subjects.add(w.subject)
            for e in w.evidence:
                fraud_subjects.add(e)
            fraud_amounts[w.subject] = w.amount_cents
            if w.payload.get("duplicate_of"):
                fraud_subjects.add(str(w.payload["duplicate_of"]))

    for e in sow.audit.all():
        if not e.get("allowed") and e.get("action") in ("approve", "post"):
            fraud_subjects.add(e.get("subject", ""))

    supply = _supply_chain_graph(chain, fraud_subjects, fraud_amounts, sow)
    context = _context_graph(money, fraud_subjects, fraud_amounts, sow, ledger)
    relationships = _relationship_graph(ledger, sow, fraud_subjects, fraud_amounts)

    return {
        "supply_chain": supply,
        "context": context,
        "relationships": relationships,
        "legend": {
            "fraud": "Red dashed edges / nodes — blocked, duplicate, or denied",
            "hold": "Amber — awaiting owner Approve",
            "posted": "Green — gateway posted to system of record",
            "amounts": "Edge labels are exact USD from ledger / work items",
        },
        "stats": {
            "nodes": len(supply["nodes"]) + len(context["nodes"]) + len(relationships["nodes"]),
            "edges": len(supply["edges"]) + len(context["edges"]) + len(relationships["edges"]),
            "fraud_flags": len([n for n in context["nodes"] if n.get("fraud")]),
            "supply_tiers": len({n.get("tier") for n in supply["nodes"]}),
            "cash_balance_usd": _usd(sow.cash_balance_cents),
            "runway_days": round(sow.runway_days, 2),
        },
    }


def _mark_fraud(node: dict[str, Any], fraud_subjects: set[str], fraud_amounts: dict[str, int]) -> dict[str, Any]:
    ids = {node["id"], *node.get("aliases", [])}
    if ids & fraud_subjects:
        node = {**node, "fraud": True}
        if not node.get("amount_cents"):
            for sid in ids:
                if sid in fraud_amounts:
                    node["amount_cents"] = fraud_amounts[sid]
                    node["amount_label"] = _usd(fraud_amounts[sid])
                    break
    return node


def _supply_chain_graph(
    chain: dict[str, Any],
    fraud_subjects: set[str],
    fraud_amounts: dict[str, int],
    sow: SystemOfWork,
) -> dict[str, Any]:
    nodes = []
    for n in chain.get("nodes", []):
        node = {
            "id": n["id"],
            "label": n["name"],
            "kind": n.get("kind", "entity"),
            "tier": n.get("tier", 0),
            "tier_label": n.get("tier_label", ""),
            "amount_cents": n.get("monthly_cents", 0),
            "amount_label": _usd(n.get("monthly_cents", 0)),
            "fraud": False,
            "held": False,
            "meta": n.get("meta", {}),
        }
        nodes.append(_mark_fraud(node, fraud_subjects, fraud_amounts))

    # Mark alt flour / spike path if procurement work exists
    for w in sow.work_items.values():
        if w.kind == "procurement" and w.payload.get("to_supplier"):
            for node in nodes:
                if node["id"] == w.payload["to_supplier"]:
                    node["meta"] = {**node.get("meta", {}), "counter_offer": True}
                if node["id"] == w.subject or node["id"] == w.payload.get("from"):
                    node["meta"] = {**node.get("meta", {}), "price_spike": True}

    edges = []
    for e in chain.get("edges", []):
        fraud = bool({e["from"], e["to"]} & fraud_subjects) or e.get("fraud", False)
        amt = int(e.get("amount_cents", 0))
        edges.append(
            {
                "id": e.get("id", f"{e['from']}->{e['to']}"),
                "source": e["from"],
                "target": e["to"],
                "amount_cents": amt,
                "amount_label": _usd(amt),
                "label": e.get("label", _usd(amt)),
                "kind": e.get("kind", "goods"),
                "fraud": fraud or e.get("fraud", False),
                "held": e.get("held", False),
            }
        )

    # Overlay live hold on supplier deposit edge
    for w in sow.work_items.values():
        if w.state == "HELD" and w.kind == "spend_hold":
            edges.append(
                {
                    "id": f"hold-{w.id}",
                    "source": "maya-bakery",
                    "target": "sup-flour-co",
                    "amount_cents": w.amount_cents,
                    "amount_label": _usd(w.amount_cents),
                    "label": f"HOLD {_usd(w.amount_cents)}",
                    "kind": "payment",
                    "fraud": False,
                    "held": True,
                }
            )

    return {
        "id": "supply_chain",
        "title": "Full supply chain",
        "subtitle": "Origins → processors → bakery → wholesale → cafes (monthly $)",
        "layout": "hierarchical",
        "nodes": nodes,
        "edges": edges,
    }


def _context_graph(
    money: dict[str, Any],
    fraud_subjects: set[str],
    fraud_amounts: dict[str, int],
    sow: SystemOfWork,
    ledger: dict[str, Any],
) -> dict[str, Any]:
    """Money + policy context graph — the 'why is this connected' view."""
    nodes = []
    for n in money.get("nodes", []):
        node = {
            "id": n["id"],
            "label": n["name"],
            "kind": n.get("kind", "account"),
            "amount_cents": n.get("amount_cents", 0),
            "amount_label": _usd(n.get("amount_cents", 0)),
            "fraud": n.get("fraud", False),
            "held": n.get("held", False),
            "aliases": n.get("aliases", []),
            "meta": n.get("meta", {}),
        }
        nodes.append(_mark_fraud(node, fraud_subjects, fraud_amounts))

    # Live cash node
    nodes.append(
        {
            "id": "cash-operating",
            "label": "Operating cash",
            "kind": "cash",
            "amount_cents": sow.cash_balance_cents,
            "amount_label": _usd(sow.cash_balance_cents),
            "fraud": False,
            "held": False,
            "meta": {"runway_days": round(sow.runway_days, 1)},
        }
    )

    # Policy nodes
    for p in sow.policies.values():
        nodes.append(
            {
                "id": p.id,
                "label": p.id,
                "kind": "policy",
                "amount_cents": 0,
                "amount_label": p.status,
                "fraud": False,
                "held": p.status == "needs_approval",
                "meta": {"rule": p.rule, "title": p.title},
            }
        )

    edges = []
    for e in money.get("edges", []):
        amt = int(e.get("amount_cents", 0))
        fraud = e.get("fraud", False) or bool({e["from"], e["to"]} & fraud_subjects)
        if e.get("id") in fraud_subjects or e.get("invoice_id") in fraud_subjects:
            fraud = True
            amt = fraud_amounts.get(e.get("invoice_id", ""), amt) or amt
        edges.append(
            {
                "id": e.get("id", f"{e['from']}->{e['to']}"),
                "source": e["from"],
                "target": e["to"],
                "amount_cents": amt,
                "amount_label": _usd(amt),
                "label": e.get("label", _usd(amt)),
                "kind": e.get("kind", "payment"),
                "fraud": fraud,
                "held": e.get("held", False),
                "policy_id": e.get("policy_id"),
            }
        )

    # Wire live work items as context edges
    for w in sow.work_items.values():
        if w.amount_cents <= 0 and w.kind != "forecast":
            continue
        src, tgt = "maya-bakery", w.subject
        if w.kind == "ar_collect":
            src, tgt = w.subject, "cash-operating"
        elif w.kind == "cash_match":
            src, tgt = w.subject, "cash-operating"
        elif w.kind in ("ap_invoice", "spend_hold", "procurement"):
            src, tgt = "cash-operating", w.subject
        elif w.kind == "forecast":
            src, tgt = "cash-operating", "runway"
            nodes.append(
                {
                    "id": "runway",
                    "label": f"Runway {sow.runway_days:.0f}d",
                    "kind": "forecast",
                    "amount_cents": sow.cash_balance_cents,
                    "amount_label": _usd(sow.cash_balance_cents),
                    "fraud": False,
                    "held": False,
                    "meta": {},
                }
            )

        fraud = bool(w.payload.get("blocked")) or w.state == "BLOCKED"
        edges.append(
            {
                "id": f"wi-{w.id}",
                "source": src,
                "target": tgt,
                "amount_cents": w.amount_cents,
                "amount_label": _usd(w.amount_cents),
                "label": f"{w.state} {_usd(w.amount_cents)}" if w.amount_cents else w.state,
                "kind": w.kind,
                "fraud": fraud,
                "held": w.state == "HELD",
                "policy_id": w.policy_id,
                "work_item_id": w.id,
            }
        )

        if w.policy_id:
            edges.append(
                {
                    "id": f"pol-{w.id}",
                    "source": w.policy_id,
                    "target": w.subject,
                    "amount_cents": 0,
                    "amount_label": w.policy_id,
                    "label": w.policy_id,
                    "kind": "policy_link",
                    "fraud": False,
                    "held": False,
                    "policy_id": w.policy_id,
                }
            )

    # Ensure bakery hub exists
    if not any(n["id"] == "maya-bakery" for n in nodes):
        nodes.insert(
            0,
            {
                "id": "maya-bakery",
                "label": ledger.get("business", "Maya's Bakery"),
                "kind": "company",
                "amount_cents": sow.cash_balance_cents,
                "amount_label": _usd(sow.cash_balance_cents),
                "fraud": False,
                "held": False,
                "meta": {"owner": ledger.get("owner", "Maya")},
            },
        )

    return {
        "id": "context",
        "title": "Context graph",
        "subtitle": "Cash, invoices, policies, and live work — exact dollars",
        "layout": "force",
        "nodes": _dedupe_nodes(nodes),
        "edges": edges,
    }


def _relationship_graph(
    ledger: dict[str, Any],
    sow: SystemOfWork,
    fraud_subjects: set[str],
    fraud_amounts: dict[str, int],
) -> dict[str, Any]:
    """Entity relationship graph: vendors ↔ bank fingerprints ↔ customers ↔ GL."""
    nodes: list[dict[str, Any]] = [
        {
            "id": "maya-bakery",
            "label": "Maya's Bakery",
            "kind": "company",
            "amount_cents": sow.cash_balance_cents,
            "amount_label": _usd(sow.cash_balance_cents),
            "fraud": False,
            "held": False,
            "meta": {},
        },
        {
            "id": "bank-jpm",
            "label": "JPM operating",
            "kind": "bank",
            "amount_cents": sow.cash_balance_cents,
            "amount_label": _usd(sow.cash_balance_cents),
            "fraud": False,
            "held": False,
            "meta": {},
        },
        {
            "id": "gl-6850",
            "label": "GL 6850 Bank Fees",
            "kind": "gl",
            "amount_cents": 0,
            "amount_label": "fees",
            "fraud": False,
            "held": False,
            "meta": {},
        },
    ]
    edges: list[dict[str, Any]] = [
        {
            "id": "rel-cash",
            "source": "maya-bakery",
            "target": "bank-jpm",
            "amount_cents": sow.cash_balance_cents,
            "amount_label": _usd(sow.cash_balance_cents),
            "label": _usd(sow.cash_balance_cents),
            "kind": "owns",
            "fraud": False,
            "held": False,
        }
    ]

    for s in ledger.get("suppliers", []):
        nodes.append(
            _mark_fraud(
                {
                    "id": s["id"],
                    "label": s["name"],
                    "kind": "vendor",
                    "amount_cents": s.get("unit_price_cents", 0),
                    "amount_label": _usd(s.get("unit_price_cents", 0)) + "/unit",
                    "fraud": False,
                    "held": False,
                    "aliases": [s.get("bank_fingerprint", "")],
                    "meta": {"trust": s.get("trust_score"), "category": s.get("category")},
                },
                fraud_subjects,
                fraud_amounts,
            )
        )
        bank_id = s.get("bank_fingerprint", f"bank-{s['id']}")
        nodes.append(
            {
                "id": bank_id,
                "label": bank_id,
                "kind": "bank_fp",
                "amount_cents": 0,
                "amount_label": "fingerprint",
                "fraud": bank_id in fraud_subjects,
                "held": False,
                "meta": {},
            }
        )
        edges.append(
            {
                "id": f"rel-{s['id']}-bank",
                "source": s["id"],
                "target": bank_id,
                "amount_cents": 0,
                "amount_label": "pays via",
                "label": "pays via",
                "kind": "bank_link",
                "fraud": False,
                "held": False,
            }
        )
        # Aggregate AP volume from invoices
        vol = sum(
            i["amount_cents"]
            for i in ledger.get("invoices", [])
            if i.get("vendor_id") == s["id"]
        )
        edges.append(
            {
                "id": f"rel-ap-{s['id']}",
                "source": "maya-bakery",
                "target": s["id"],
                "amount_cents": vol,
                "amount_label": _usd(vol),
                "label": f"AP {_usd(vol)}",
                "kind": "payable",
                "fraud": s["id"] in fraud_subjects,
                "held": False,
            }
        )

    # Customers from money graph / late AR
    customers = ledger.get("customers") or [
        {"id": "cust-harbor", "name": "Harbor Cafe Group", "ar_cents": 920_000},
        {"id": "cust-summit", "name": "Summit Grocery", "ar_cents": 4_800_00},
        {"id": "cust-oak", "name": "Oak Street Market", "ar_cents": 2_150_00},
        {"id": "cust-wholesale", "name": "Bay Area Wholesale", "ar_cents": 12_400_00},
    ]
    for c in customers:
        nodes.append(
            {
                "id": c["id"],
                "label": c["name"],
                "kind": "customer",
                "amount_cents": c.get("ar_cents", 0),
                "amount_label": _usd(c.get("ar_cents", 0)),
                "fraud": False,
                "held": False,
                "meta": {},
            }
        )
        edges.append(
            {
                "id": f"rel-ar-{c['id']}",
                "source": c["id"],
                "target": "maya-bakery",
                "amount_cents": c.get("ar_cents", 0),
                "amount_label": _usd(c.get("ar_cents", 0)),
                "label": f"AR {_usd(c.get('ar_cents', 0))}",
                "kind": "receivable",
                "fraud": False,
                "held": False,
            }
        )

    # Duplicate fraud relationship highlight
    if fraud_amounts:
        for sub, amt in fraud_amounts.items():
            edges.append(
                {
                    "id": f"fraud-{sub}",
                    "source": "sup-flour-co",
                    "target": "maya-bakery",
                    "amount_cents": amt,
                    "amount_label": _usd(amt),
                    "label": f"FRAUD {_usd(amt)}",
                    "kind": "fraud",
                    "fraud": True,
                    "held": False,
                }
            )

    # Short wire → GL fees
    for w in sow.work_items.values():
        if w.kind == "cash_match" and w.payload.get("gap_cents"):
            gap = int(w.payload["gap_cents"])
            edges.append(
                {
                    "id": f"fee-{w.id}",
                    "source": "bank-jpm",
                    "target": "gl-6850",
                    "amount_cents": gap,
                    "amount_label": _usd(gap),
                    "label": f"short {_usd(gap)}",
                    "kind": "fee",
                    "fraud": False,
                    "held": False,
                    "policy_id": w.policy_id or "pol-001",
                }
            )

    return {
        "id": "relationships",
        "title": "Relationship graph",
        "subtitle": "Vendors, bank fingerprints, customers, GL — who touches whom",
        "layout": "force",
        "nodes": _dedupe_nodes(nodes),
        "edges": edges,
    }


def _dedupe_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for n in nodes:
        prev = seen.get(n["id"])
        if prev is None:
            seen[n["id"]] = n
        else:
            # Prefer fraud / higher amount
            if n.get("fraud"):
                prev["fraud"] = True
            if n.get("amount_cents", 0) > prev.get("amount_cents", 0):
                prev["amount_cents"] = n["amount_cents"]
                prev["amount_label"] = n.get("amount_label", prev.get("amount_label"))
    return list(seen.values())


def _default_supply_chain() -> dict[str, Any]:
    return {
        "nodes": [
            {"id": "farm-wheat", "name": "Sacramento Wheat Co-op", "kind": "origin", "tier": 0, "tier_label": "Origin", "monthly_cents": 48_000_00},
            {"id": "farm-dairy", "name": "Petaluma Dairy Farms", "kind": "origin", "tier": 0, "tier_label": "Origin", "monthly_cents": 36_000_00},
            {"id": "mill-coastal", "name": "Coastal Grain Mill", "kind": "processor", "tier": 1, "tier_label": "Processor", "monthly_cents": 52_000_00},
            {"id": "sup-flour-co", "name": "North Bay Flour Co", "kind": "distributor", "tier": 2, "tier_label": "Distributor", "monthly_cents": 18_200_00},
            {"id": "sup-alt-flour", "name": "Coastal Grain Alt", "kind": "distributor", "tier": 2, "tier_label": "Distributor", "monthly_cents": 14_800_00},
            {"id": "sup-dairy", "name": "Valley Dairy", "kind": "distributor", "tier": 2, "tier_label": "Distributor", "monthly_cents": 12_400_00},
            {"id": "sup-packaging", "name": "ClearWrap Packaging", "kind": "packaging", "tier": 2, "tier_label": "Packaging", "monthly_cents": 4_200_00},
            {"id": "plant-ink", "name": "EcoInk Labels", "kind": "packaging", "tier": 2, "tier_label": "Packaging", "monthly_cents": 980_00},
            {"id": "cold-chain", "name": "Bay Cold Logistics", "kind": "logistics", "tier": 3, "tier_label": "Logistics", "monthly_cents": 3_600_00},
            {"id": "maya-bakery", "name": "Maya's Bakery (HQ)", "kind": "company", "tier": 4, "tier_label": "Production", "monthly_cents": 62_000_00},
            {"id": "site-mission", "name": "Mission Pop-up", "kind": "site", "tier": 5, "tier_label": "Channels", "monthly_cents": 14_200_00},
            {"id": "site-oakland", "name": "Oakland Kitchen", "kind": "site", "tier": 5, "tier_label": "Channels", "monthly_cents": 22_800_00},
            {"id": "cust-wholesale", "name": "Bay Area Wholesale", "kind": "customer", "tier": 6, "tier_label": "Wholesale", "monthly_cents": 28_500_00},
            {"id": "cust-harbor", "name": "Harbor Cafe Group", "kind": "customer", "tier": 6, "tier_label": "Foodservice", "monthly_cents": 9_200_00},
            {"id": "cust-summit", "name": "Summit Grocery", "kind": "customer", "tier": 6, "tier_label": "Retail", "monthly_cents": 11_400_00},
            {"id": "cust-oak", "name": "Oak Street Market", "kind": "customer", "tier": 6, "tier_label": "Retail", "monthly_cents": 6_800_00},
        ],
        "edges": [
            {"from": "farm-wheat", "to": "mill-coastal", "amount_cents": 48_000_00, "label": "wheat $48,000", "kind": "goods"},
            {"from": "mill-coastal", "to": "sup-flour-co", "amount_cents": 28_400_00, "label": "flour $28,400", "kind": "goods"},
            {"from": "mill-coastal", "to": "sup-alt-flour", "amount_cents": 22_100_00, "label": "flour $22,100", "kind": "goods"},
            {"from": "farm-dairy", "to": "sup-dairy", "amount_cents": 36_000_00, "label": "milk $36,000", "kind": "goods"},
            {"from": "sup-flour-co", "to": "maya-bakery", "amount_cents": 18_200_00, "label": "AP $18,200/mo", "kind": "goods"},
            {"from": "sup-alt-flour", "to": "maya-bakery", "amount_cents": 0, "label": "alt (trial)", "kind": "goods"},
            {"from": "sup-dairy", "to": "maya-bakery", "amount_cents": 12_400_00, "label": "AP $12,400/mo", "kind": "goods"},
            {"from": "sup-packaging", "to": "maya-bakery", "amount_cents": 4_200_00, "label": "AP $4,200/mo", "kind": "goods"},
            {"from": "plant-ink", "to": "sup-packaging", "amount_cents": 980_00, "label": "labels $980", "kind": "goods"},
            {"from": "cold-chain", "to": "maya-bakery", "amount_cents": 3_600_00, "label": "freight $3,600", "kind": "logistics"},
            {"from": "maya-bakery", "to": "site-mission", "amount_cents": 14_200_00, "label": "transfer $14,200", "kind": "internal"},
            {"from": "maya-bakery", "to": "site-oakland", "amount_cents": 22_800_00, "label": "transfer $22,800", "kind": "internal"},
            {"from": "maya-bakery", "to": "cust-wholesale", "amount_cents": 28_500_00, "label": "rev $28,500", "kind": "revenue"},
            {"from": "site-oakland", "to": "cust-harbor", "amount_cents": 9_200_00, "label": "rev $9,200", "kind": "revenue"},
            {"from": "site-mission", "to": "cust-summit", "amount_cents": 11_400_00, "label": "rev $11,400", "kind": "revenue"},
            {"from": "site-mission", "to": "cust-oak", "amount_cents": 6_800_00, "label": "rev $6,800", "kind": "revenue"},
            # Fraudulent duplicate AP attempt in the chain
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


def _default_money_graph() -> dict[str, Any]:
    return {
        "nodes": [
            {"id": "maya-bakery", "name": "Maya's Bakery", "kind": "company", "amount_cents": 1_840_000},
            {"id": "sup-flour-co", "name": "North Bay Flour", "kind": "vendor", "amount_cents": 18_200_00},
            {"id": "sup-dairy", "name": "Valley Dairy", "kind": "vendor", "amount_cents": 12_400_00},
            {"id": "inv-dup-incoming", "name": "INV dup $4,200", "kind": "invoice", "amount_cents": 420_000, "fraud": True, "aliases": ["inv-dup-original"]},
            {"id": "inv-dup-original", "name": "INV paid $4,200", "kind": "invoice", "amount_cents": 420_000},
            {"id": "JPM-88310442", "name": "Wire $57,975", "kind": "bank_txn", "amount_cents": 5_797_500},
            {"id": "ar-big-cafe", "name": "AR Harbor $9,200", "kind": "receivable", "amount_cents": 920_000},
            {"id": "appr-supplier-deposit", "name": "Deposit $1,400", "kind": "payment", "amount_cents": 140_000, "held": True},
        ],
        "edges": [
            {"from": "maya-bakery", "to": "sup-flour-co", "amount_cents": 18_200_00, "kind": "payment", "label": "$18,200/mo"},
            {"from": "maya-bakery", "to": "sup-dairy", "amount_cents": 12_400_00, "kind": "payment", "label": "$12,400/mo"},
            {"id": "inv-dup-incoming", "from": "sup-flour-co", "to": "maya-bakery", "amount_cents": 420_000, "kind": "invoice", "fraud": True, "invoice_id": "inv-dup-incoming", "label": "FRAUD $4,200"},
            {"from": "inv-dup-original", "to": "sup-flour-co", "amount_cents": 420_000, "kind": "paid", "label": "paid $4,200"},
            {"from": "JPM-88310442", "to": "maya-bakery", "amount_cents": 5_797_500, "kind": "wire", "label": "$57,975 (−$25)"},
            {"from": "ar-big-cafe", "to": "maya-bakery", "amount_cents": 920_000, "kind": "ar", "label": "$9,200 late"},
            {"from": "maya-bakery", "to": "appr-supplier-deposit", "amount_cents": 140_000, "kind": "hold", "held": True, "label": "HOLD $1,400"},
        ],
    }


def export_graphs_json(sow: SystemOfWork, path: Path | None = None) -> Path:
    path = path or Path(__file__).resolve().parents[2] / "data" / "seed" / "graphs.json"
    data = build_graphs(sow)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path