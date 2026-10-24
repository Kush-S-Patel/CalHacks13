"""Merge ERP vault entities into SwarmCFO graph payloads."""

from __future__ import annotations

from typing import Any

from erp.business.store import BIZ
from erp.store import ERP
from sow.graphs import build_graphs
from sow.store import SystemOfWork


def _usd(cents: int) -> str:
    return f"${cents / 100:,.0f}"


def build_erp_graphs(sow: SystemOfWork) -> dict[str, Any]:
    base = build_graphs(sow)
    snap = ERP.snapshot()
    if not snap["parties"] and not snap["flows"]:
        base["erp"] = {"merged": False, "documents": len(snap["documents"])}
        return base

    # --- Supply chain from ERP parties/flows ---
    sc_nodes = []
    for p in snap["parties"]:
        sc_nodes.append(
            {
                "id": p["id"],
                "label": p["name"],
                "kind": p["role"] if p["role"] != "company" else "company",
                "tier": p.get("tier") or 0,
                "tier_label": _tier_label(p.get("tier") or 0),
                "amount_cents": p.get("amount_cents") or 0,
                "amount_label": _usd(p.get("amount_cents") or 0),
                "fraud": False,
                "held": False,
                "meta": p.get("meta") or {},
            }
        )
    # ensure hub
    if not any(n["id"] == "maya-bakery" for n in sc_nodes):
        sc_nodes.append(
            {
                "id": "maya-bakery",
                "label": "Maya's Bakery (HQ)",
                "kind": "company",
                "tier": 4,
                "tier_label": "Production",
                "amount_cents": sow.cash_balance_cents,
                "amount_label": _usd(sow.cash_balance_cents),
                "fraud": False,
                "held": False,
                "meta": {},
            }
        )

    sc_edges = []
    for f in snap["flows"]:
        sc_edges.append(
            {
                "id": f["id"],
                "source": f["source_id"],
                "target": f["target_id"],
                "amount_cents": f["amount_cents"],
                "amount_label": _usd(f["amount_cents"]),
                "label": _usd(f["amount_cents"]),
                "kind": f.get("kind") or "goods",
                "fraud": bool(f.get("fraud")),
                "held": False,
            }
        )

    if sc_nodes and sc_edges:
        base["supply_chain"] = {
            "id": "supply_chain",
            "title": "Full supply chain (from ERP vault)",
            "subtitle": f"Built from {len(snap['documents'])} stored documents · exact dollars",
            "layout": "hierarchical",
            "nodes": sc_nodes,
            "edges": sc_edges,
        }

    # --- Context: accounts + fraud + cash ---
    ctx_nodes = [
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
            "id": "cash-operating",
            "label": "Operating cash",
            "kind": "cash",
            "amount_cents": sow.cash_balance_cents,
            "amount_label": _usd(sow.cash_balance_cents),
            "fraud": False,
            "held": False,
            "meta": {"runway_days": round(sow.runway_days, 1)},
        },
    ]
    for a in snap["accounts"][:20]:
        ctx_nodes.append(
            {
                "id": f"gl-{a['code']}",
                "label": f"{a['code']} {a['name']}"[:28],
                "kind": "gl",
                "amount_cents": a["balance_cents"],
                "amount_label": _usd(a["balance_cents"]),
                "fraud": False,
                "held": False,
                "meta": {"type": a["account_type"]},
            }
        )
    for p in snap["parties"][:25]:
        ctx_nodes.append(
            {
                "id": p["id"],
                "label": p["name"],
                "kind": "vendor" if p["role"] == "vendor" else p["role"],
                "amount_cents": p["amount_cents"],
                "amount_label": _usd(p["amount_cents"]),
                "fraud": False,
                "held": False,
                "meta": {},
            }
        )

    ctx_edges = []
    for f in snap["flows"]:
        ctx_edges.append(
            {
                "id": f["id"],
                "source": f["source_id"],
                "target": f["target_id"],
                "amount_cents": f["amount_cents"],
                "amount_label": _usd(f["amount_cents"]),
                "label": ("FRAUD " if f.get("fraud") else "") + _usd(f["amount_cents"]),
                "kind": f.get("kind") or "payment",
                "fraud": bool(f.get("fraud")),
                "held": False,
            }
        )
    for a in snap["accounts"][:12]:
        ctx_edges.append(
            {
                "id": f"gl-link-{a['code']}",
                "source": "maya-bakery",
                "target": f"gl-{a['code']}",
                "amount_cents": a["balance_cents"],
                "amount_label": _usd(a["balance_cents"]),
                "label": _usd(a["balance_cents"]),
                "kind": "gl",
                "fraud": False,
                "held": False,
            }
        )

    base["context"] = {
        "id": "context",
        "title": "Context graph (ERP + live cash)",
        "subtitle": "GL accounts, parties, and money flows from uploaded workbooks",
        "layout": "force",
        "nodes": _dedupe(ctx_nodes),
        "edges": ctx_edges,
    }

    # --- Per-business DocILE enterprise graphs (top by invoice volume) ---
    biz_summaries = BIZ.list_summaries()[:8]
    enterprise_graphs = []
    for s in biz_summaries[:3]:
        g = BIZ.graph_for(s["id"])
        if g and g.get("nodes"):
            enterprise_graphs.append(g)
    if enterprise_graphs:
        # surface the richest business as a dedicated graph panel
        top = enterprise_graphs[0]
        base["enterprise"] = {
            **top,
            "id": "enterprise",
            "title": top.get("title") or "Enterprise (DocILE)",
            "subtitle": top.get("subtitle")
            or "Customers + supply links learned per issuing vendor",
        }
    base["businesses"] = biz_summaries

    base["erp"] = {
        "merged": True,
        "documents": len(snap["documents"]),
        "accounts": len(snap["accounts"]),
        "parties": len(snap["parties"]),
        "flows": len(snap["flows"]),
        "businesses": len(BIZ.profiles),
    }
    base["stats"]["erp_documents"] = len(snap["documents"])
    base["stats"]["businesses"] = len(BIZ.profiles)
    base["stats"]["fraud_flags"] = len([e for e in ctx_edges if e.get("fraud")])
    return base


def _tier_label(tier: int) -> str:
    return {
        0: "Origin",
        1: "Processor",
        2: "Distributor",
        3: "Logistics",
        4: "Production",
        5: "Channels",
        6: "Customers",
    }.get(tier, f"Tier {tier}")


def _dedupe(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for n in nodes:
        prev = seen.get(n["id"])
        if not prev:
            seen[n["id"]] = n
        elif n.get("amount_cents", 0) > prev.get("amount_cents", 0):
            seen[n["id"]] = n
    return list(seen.values())