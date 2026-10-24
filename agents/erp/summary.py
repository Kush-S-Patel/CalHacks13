"""Enterprise summary — whole-business + supply-chain dynamics for the Summary tab."""

from __future__ import annotations

from typing import Any

from erp.store import ERP


def _usd(cents: int) -> str:
    return f"${cents / 100:,.0f}"


def build_enterprise_summary(sow_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snap = ERP.snapshot()
    totals = snap["totals"]
    sow = sow_snapshot or {}

    vendors = [p for p in snap["parties"] if p["role"] in {"vendor", "distributor", "origin", "logistics", "packaging"}]
    customers = [p for p in snap["parties"] if p["role"] == "customer"]
    fraud_flows = [f for f in snap["flows"] if f.get("fraud")]
    supply_flows = [f for f in snap["flows"] if f.get("kind") in {"goods", "payable", "logistics"}]
    revenue_flows = [f for f in snap["flows"] if f.get("kind") in {"revenue", "receivable"}]

    concentration = _vendor_concentration(vendors)
    chain_depth = max((p.get("tier") or 0 for p in snap["parties"]), default=0) + 1

    cash = int(sow.get("cash_balance_cents") or 1_840_000)
    burn = int(sow.get("daily_burn_cents") or 165_000)
    runway = cash / burn if burn else 0

    health_score = _health_score(
        runway=runway,
        fraud_n=len(fraud_flows),
        docs=totals["documents"],
        concentration=concentration["top_share"],
        ar=totals["ar_cents"],
        ap=totals["ap_cents"],
    )

    return {
        "title": "Enterprise summary",
        "subtitle": "Accounts, revenue, supply chain, and operational risk in one place",
        "health_score": health_score,
        "kpis": [
            {"id": "cash", "label": "Operating cash", "value": _usd(cash), "hint": f"Runway {runway:.0f} days"},
            {"id": "revenue", "label": "Revenue (indexed)", "value": _usd(totals["revenue_cents"]), "hint": f"{len(revenue_flows)} flows"},
            {"id": "ap", "label": "AP exposure", "value": _usd(totals["ap_cents"]), "hint": f"{len(vendors)} vendors"},
            {"id": "ar", "label": "AR outstanding", "value": _usd(totals["ar_cents"]), "hint": f"{len(customers)} customers"},
            {"id": "docs", "label": "Documents in vault", "value": str(totals["documents"]), "hint": "Digitally stored"},
            {"id": "fraud", "label": "Fraud-flagged flows", "value": str(len(fraud_flows)), "hint": _usd(sum(f["amount_cents"] for f in fraud_flows))},
        ],
        "supply_chain": {
            "tiers": chain_depth,
            "nodes": len(snap["parties"]),
            "links": len(supply_flows),
            "monthly_goods_cents": sum(f["amount_cents"] for f in supply_flows),
            "monthly_goods_label": _usd(sum(f["amount_cents"] for f in supply_flows)),
            "concentration": concentration,
            "top_vendors": sorted(vendors, key=lambda p: p["amount_cents"], reverse=True)[:5],
            "top_customers": sorted(customers, key=lambda p: p["amount_cents"], reverse=True)[:5],
            "dynamics": _dynamics(vendors, customers, fraud_flows, concentration),
        },
        "chart_of_accounts": {
            "count": totals["accounts"],
            "by_type": _by_type(snap["accounts"]),
            "top_balances": sorted(snap["accounts"], key=lambda a: abs(a["balance_cents"]), reverse=True)[:8],
        },
        "documents": snap["documents"][:12],
        "integrations": snap["integrations"],
        "sow": {
            "runway_days": round(float(sow.get("runway_days") or runway), 2),
            "work_items": len(sow.get("work_items") or []),
            "policies": len(sow.get("policies") or []),
            "open_holds": len(sow.get("open_holds") or []),
        },
        "recommendations": _recommendations(health_score, fraud_flows, concentration, totals),
    }


def _by_type(accounts: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for a in accounts:
        out[a["account_type"]] = out.get(a["account_type"], 0) + 1
    return out


def _vendor_concentration(vendors: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum(v["amount_cents"] for v in vendors) or 1
    ordered = sorted(vendors, key=lambda v: v["amount_cents"], reverse=True)
    top = ordered[0] if ordered else None
    top_share = (top["amount_cents"] / total) if top else 0
    return {
        "top_vendor": top["name"] if top else None,
        "top_share": round(top_share, 3),
        "top_share_pct": f"{top_share * 100:.0f}%",
        "vendor_count": len(vendors),
    }


def _dynamics(
    vendors: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    fraud: list[dict[str, Any]],
    concentration: dict[str, Any],
) -> list[str]:
    lines = []
    if concentration["top_share"] >= 0.4:
        lines.append(
            f"Supplier concentration risk: {concentration['top_vendor']} is {concentration['top_share_pct']} of indexed AP."
        )
    if len(customers) >= 1 and len(vendors) >= 1:
        lines.append(
            f"Chain spans {len(vendors)} upstream parties and {len(customers)} downstream customers."
        )
    if fraud:
        lines.append(f"{len(fraud)} money flows flagged fraudulent — review in Context graph.")
    if not lines:
        lines.append("Supply chain looks balanced from indexed documents. Upload more sheets to deepen coverage.")
    return lines


def _health_score(*, runway: float, fraud_n: int, docs: int, concentration: float, ar: int, ap: int) -> int:
    score = 70
    score += min(15, int(runway))  # longer runway
    score += min(10, docs * 2)
    score -= fraud_n * 8
    if concentration > 0.5:
        score -= 10
    elif concentration > 0.35:
        score -= 5
    if ap > 0 and ar / max(ap, 1) < 0.5:
        score -= 5
    return int(max(0, min(100, score)))


def _recommendations(
    health: int,
    fraud: list[dict[str, Any]],
    concentration: dict[str, Any],
    totals: dict[str, Any],
) -> list[str]:
    recs = []
    if fraud:
        recs.append("Open Work queue — fraud-flagged AP should be BLOCKED before gateway post.")
    if concentration.get("top_share", 0) >= 0.4:
        recs.append("Dual-source critical SKUs (see Coastal Grain Alt) to cut concentration risk.")
    if totals["documents"] < 3:
        recs.append("Upload chart of accounts + AP aging + supply-chain sheet for a complete enterprise map.")
    if totals["revenue_cents"] == 0:
        recs.append("Add a revenue export so Summary can show top customers and margin pressure.")
    if health >= 85:
        recs.append("Enterprise health is strong — keep policies active and watch runway weekly.")
    return recs