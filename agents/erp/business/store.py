"""Per-business enterprise knowledge — customers, supply chain, relationships."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from erp.models import now_iso


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "unknown").lower()).strip("-")
    return (s or "unknown")[:80]


@dataclass
class Relationship:
    counterparty: str
    role: str  # customer | supplier | logistics | related
    strength: int = 1
    amount_cents: int = 0
    docs: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BusinessProfile:
    """One enterprise learned from invoices / DocILE docs."""

    id: str
    name: str
    tax_id: str = ""
    address: str = ""
    document_types: dict[str, int] = field(default_factory=dict)
    currencies: dict[str, int] = field(default_factory=dict)
    customers: dict[str, dict[str, Any]] = field(default_factory=dict)
    suppliers: dict[str, dict[str, Any]] = field(default_factory=dict)
    relationships: list[Relationship] = field(default_factory=list)
    line_skus: dict[str, dict[str, Any]] = field(default_factory=dict)
    doc_ids: list[str] = field(default_factory=list)
    total_invoiced_cents: int = 0
    total_due_cents: int = 0
    invoice_count: int = 0
    updated_at: str = field(default_factory=now_iso)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["relationships"] = [r if isinstance(r, dict) else r.to_dict() for r in self.relationships]
        d["customer_count"] = len(self.customers)
        d["supplier_count"] = len(self.suppliers)
        d["sku_count"] = len(self.line_skus)
        return d


class BusinessKnowledge:
    """Disk-backed store: one JSON profile per business under data/erp_vault/businesses/."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[3] / "data" / "erp_vault" / "businesses"
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self.profiles: dict[str, BusinessProfile] = {}
        self._load()

    def _load(self) -> None:
        for path in self.root.glob("biz-*.json"):
            raw = json.loads(path.read_text(encoding="utf-8"))
            rels = [Relationship(**r) if isinstance(r, dict) else r for r in raw.pop("relationships", [])]
            # drop computed keys if present
            raw.pop("customer_count", None)
            raw.pop("supplier_count", None)
            raw.pop("sku_count", None)
            p = BusinessProfile(**raw, relationships=rels)
            self.profiles[p.id] = p

    def save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for p in self.profiles.values():
            path = self.root / f"{p.id}.json"
            path.write_text(json.dumps(p.to_dict(), indent=2), encoding="utf-8")
        index = {
            "updated_at": now_iso(),
            "businesses": [
                {
                    "id": p.id,
                    "name": p.name,
                    "tax_id": p.tax_id,
                    "invoice_count": p.invoice_count,
                    "total_due_cents": p.total_due_cents,
                    "customers": len(p.customers),
                    "suppliers": len(p.suppliers),
                }
                for p in sorted(self.profiles.values(), key=lambda x: -x.invoice_count)
            ],
        }
        self.index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    def get(self, biz_id: str) -> BusinessProfile | None:
        return self.profiles.get(biz_id)

    def get_by_name(self, name: str) -> BusinessProfile | None:
        sid = f"biz-{_slug(name)}"
        return self.profiles.get(sid)

    def list_summaries(self) -> list[dict[str, Any]]:
        return [
            {
                "id": p.id,
                "name": p.name,
                "tax_id": p.tax_id,
                "address": p.address[:120] if p.address else "",
                "invoice_count": p.invoice_count,
                "total_invoiced_cents": p.total_invoiced_cents,
                "total_due_cents": p.total_due_cents,
                "customer_count": len(p.customers),
                "supplier_count": len(p.suppliers),
                "sku_count": self.line_skus_count(p),
                "document_types": p.document_types,
                "updated_at": p.updated_at,
            }
            for p in sorted(self.profiles.values(), key=lambda x: -x.invoice_count)
        ]

    @staticmethod
    def line_skus_count(p: BusinessProfile) -> int:
        return len(p.line_skus)

    def upsert_from_extraction(self, extraction: dict[str, Any], *, doc_ref: str) -> BusinessProfile:
        """
        Merge a parsed DocILE (or invoice-like) extraction into the issuing enterprise.

        extraction keys (from docile_parse.fields_to_record):
          vendor_name, vendor_tax_id, vendor_address,
          customer_*, amounts, line_items, document_type, currency, ...
        """
        name = (extraction.get("vendor_name") or "").strip() or "Unknown Vendor"
        tax = str(extraction.get("vendor_tax_id") or "").strip()
        # Prefer stable tax-id identity so the same enterprise merges across name variants
        if tax:
            biz_id = f"biz-tax-{_slug(tax)}"
            existing = self.profiles.get(biz_id)
            if existing is None:
                # migrate prior name-keyed profile if present
                legacy = self.profiles.get(f"biz-{_slug(name)}")
                if legacy and not legacy.tax_id:
                    legacy.id = biz_id
                    legacy.tax_id = tax
                    self.profiles.pop(f"biz-{_slug(name)}", None)
                    self.profiles[biz_id] = legacy
                    existing = legacy
            p = existing
        else:
            biz_id = f"biz-{_slug(name)}"
            p = self.profiles.get(biz_id)

        if p is None:
            p = BusinessProfile(id=biz_id, name=name, tax_id=tax)
            self.profiles[biz_id] = p

        if tax:
            p.tax_id = tax
        if name and (p.name == "Unknown Vendor" or len(name) > len(p.name)):
            p.name = name
        if extraction.get("vendor_address"):
            p.address = str(extraction["vendor_address"]).strip()

        dtype = extraction.get("document_type") or "invoice"
        p.document_types[dtype] = p.document_types.get(dtype, 0) + 1
        cur = extraction.get("currency") or extraction.get("currency_code_amount_due") or ""
        if cur:
            p.currencies[str(cur)] = p.currencies.get(str(cur), 0) + 1

        gross = int(extraction.get("amount_total_gross_cents") or 0)
        due = int(extraction.get("amount_due_cents") or 0)
        p.total_invoiced_cents += gross
        p.total_due_cents += due
        p.invoice_count += 1
        if doc_ref and doc_ref not in p.doc_ids:
            p.doc_ids.append(doc_ref)

        # --- customers (billing / delivery) ---
        cust_name = (extraction.get("customer_billing_name") or extraction.get("customer_delivery_name") or "").strip()
        if cust_name:
            cid = _slug(cust_name)
            c = p.customers.get(cid) or {
                "id": cid,
                "name": cust_name,
                "billing_address": "",
                "delivery_address": "",
                "customer_ids": [],
                "order_ids": [],
                "invoice_count": 0,
                "amount_cents": 0,
                "docs": [],
            }
            c["invoice_count"] += 1
            c["amount_cents"] += due or gross
            if extraction.get("customer_billing_address"):
                c["billing_address"] = str(extraction["customer_billing_address"]).strip()
            if extraction.get("customer_delivery_address"):
                c["delivery_address"] = str(extraction["customer_delivery_address"]).strip()
            for key, bucket in (("customer_id", "customer_ids"), ("order_id", "order_ids"), ("customer_order_id", "order_ids")):
                val = extraction.get(key)
                if val and str(val) not in c[bucket]:
                    c[bucket].append(str(val))
            if doc_ref and doc_ref not in c["docs"]:
                c["docs"].append(doc_ref)
            p.customers[cid] = c
            self._bump_relationship(p, cust_name, "customer", due or gross, doc_ref)

        # --- line items → SKU catalog + occasional supplier/person signals ---
        for li in extraction.get("line_items") or []:
            desc = (li.get("description") or li.get("code") or "").strip()
            if not desc:
                # still catalog sparse LIR rows (qty / amount only)
                bits = [
                    str(li.get("line_item_id") or ""),
                    li.get("date") or "",
                    str(li.get("quantity") or ""),
                    str(li.get("amount_gross_cents") or ""),
                ]
                desc = " · ".join(b for b in bits if b) or ""
            if not desc:
                continue
            sid = _slug(desc)[:60]
            sku = p.line_skus.get(sid) or {
                "id": sid,
                "description": desc,
                "code": li.get("code") or "",
                "qty": 0.0,
                "amount_cents": 0,
                "hits": 0,
            }
            sku["hits"] += 1
            sku["qty"] += float(li.get("quantity") or 0)
            sku["amount_cents"] += int(li.get("amount_gross_cents") or 0)
            if li.get("code"):
                sku["code"] = str(li["code"])
            p.line_skus[sid] = sku

            person = (li.get("person_name") or "").strip()
            if person and person.lower() != name.lower():
                # treat named line parties as related supply-chain actors
                self._bump_relationship(p, person, "related", int(li.get("amount_gross_cents") or 0), doc_ref)
                pid = _slug(person)
                s = p.suppliers.get(pid) or {
                    "id": pid,
                    "name": person,
                    "role": "line_party",
                    "hits": 0,
                    "amount_cents": 0,
                    "docs": [],
                }
                s["hits"] += 1
                s["amount_cents"] += int(li.get("amount_gross_cents") or 0)
                if doc_ref and doc_ref not in s["docs"]:
                    s["docs"].append(doc_ref)
                p.suppliers[pid] = s

        p.updated_at = now_iso()
        p.meta["corpus"] = extraction.get("corpus") or p.meta.get("corpus") or "docile"
        p.meta["last_document_id"] = extraction.get("document_id") or p.meta.get("last_document_id")
        return p

    def _bump_relationship(
        self,
        p: BusinessProfile,
        counterparty: str,
        role: str,
        amount_cents: int,
        doc_ref: str,
    ) -> None:
        for r in p.relationships:
            if r.counterparty.lower() == counterparty.lower() and r.role == role:
                r.strength += 1
                r.amount_cents += amount_cents
                if doc_ref and doc_ref not in r.docs:
                    r.docs.append(doc_ref)
                return
        p.relationships.append(
            Relationship(
                counterparty=counterparty,
                role=role,
                strength=1,
                amount_cents=amount_cents,
                docs=[doc_ref] if doc_ref else [],
            )
        )

    def graph_for(self, biz_id: str) -> dict[str, Any] | None:
        p = self.profiles.get(biz_id)
        if not p:
            return None
        nodes = [
            {
                "id": p.id,
                "label": p.name,
                "kind": "company",
                "tier": 4,
                "amount_cents": p.total_due_cents,
                "meta": {"tax_id": p.tax_id, "invoices": p.invoice_count},
            }
        ]
        edges = []
        for c in p.customers.values():
            nodes.append(
                {
                    "id": f"{p.id}-cust-{c['id']}",
                    "label": c["name"],
                    "kind": "customer",
                    "tier": 1,
                    "amount_cents": c["amount_cents"],
                    "meta": {"invoices": c["invoice_count"]},
                }
            )
            edges.append(
                {
                    "id": f"e-{p.id}-{c['id']}",
                    "source": p.id,
                    "target": f"{p.id}-cust-{c['id']}",
                    "amount_cents": c["amount_cents"],
                    "kind": "receivable",
                    "label": f"${c['amount_cents']/100:,.0f}",
                }
            )
        for s in list(p.suppliers.values())[:40]:
            nodes.append(
                {
                    "id": f"{p.id}-sup-{s['id']}",
                    "label": s["name"],
                    "kind": "vendor",
                    "tier": 2,
                    "amount_cents": s["amount_cents"],
                    "meta": {"hits": s["hits"]},
                }
            )
            edges.append(
                {
                    "id": f"e-{p.id}-s-{s['id']}",
                    "source": f"{p.id}-sup-{s['id']}",
                    "target": p.id,
                    "amount_cents": s["amount_cents"],
                    "kind": "payable",
                    "label": f"${s['amount_cents']/100:,.0f}",
                }
            )
        return {
            "id": f"biz-{p.id}",
            "title": f"{p.name} — enterprise graph",
            "subtitle": f"{p.invoice_count} docs · {len(p.customers)} customers · {len(p.suppliers)} supply links",
            "layout": "hierarchical",
            "nodes": nodes,
            "edges": edges,
            "profile": {
                "tax_id": p.tax_id,
                "address": p.address,
                "total_due_cents": p.total_due_cents,
                "document_types": p.document_types,
            },
        }


BIZ = BusinessKnowledge()
