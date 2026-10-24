"""
Ingest DocILE annotations into:
  1) per-business knowledge store (customers, supply chain, relationships)
  2) ERP vault parties / money flows (for suite graphs)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from erp.business.store import BIZ
from erp.intake.docile_parse import (
    DOCILE_ROOT,
    annotation_to_record,
    fieldtype_catalog,
    iter_annotation_paths,
    load_annotation,
    resolve_docile_roots,
)
from erp.models import MoneyFlow, Party, StoredDocument, new_id, now_iso
from erp.store import ERP


def _party_id(prefix: str, name: str) -> str:
    from erp.business.store import _slug

    return f"{prefix}-{_slug(name)}"


def record_to_erp(record: dict[str, Any], *, doc_id: str) -> dict[str, Any]:
    """Map one DocILE record into ERP parties + AR/AP-style flows."""
    parties: list[Party] = []
    flows: list[MoneyFlow] = []

    vendor = (record.get("vendor_name") or "").strip()
    if not vendor:
        return {"parties": parties, "flows": flows}

    vid = _party_id("vendor", vendor)
    due = int(record.get("amount_due_cents") or record.get("amount_total_gross_cents") or 0)
    parties.append(
        Party(
            id=vid,
            name=vendor,
            role="vendor",
            tier=2,
            amount_cents=due,
            meta={
                "tax_id": record.get("vendor_tax_id"),
                "address": record.get("vendor_address"),
                "corpus": "rossumai/docile",
                "document_type": record.get("document_type"),
            },
        )
    )

    cust = (record.get("customer_billing_name") or record.get("customer_delivery_name") or "").strip()
    if cust:
        cid = _party_id("cust", cust)
        parties.append(
            Party(
                id=cid,
                name=cust,
                role="customer",
                tier=1,
                amount_cents=due,
                meta={
                    "billing_address": record.get("customer_billing_address"),
                    "delivery_address": record.get("customer_delivery_address"),
                    "customer_id": record.get("customer_id"),
                    "corpus": "rossumai/docile",
                },
            )
        )
        # vendor → customer receivable on this invoice
        flows.append(
            MoneyFlow(
                id=new_id("flow"),
                source_id=vid,
                target_id=cid,
                amount_cents=due,
                kind="receivable",
                doc_id=doc_id,
                memo=f"DocILE {record.get('document_type')} #{record.get('document_id') or ''}".strip(),
            )
        )
        # also link HQ hub ↔ vendor for supply-chain view
        flows.append(
            MoneyFlow(
                id=new_id("flow"),
                source_id=vid,
                target_id="maya-bakery",
                amount_cents=due,
                kind="payable",
                doc_id=doc_id,
                memo="DocILE vendor in network",
            )
        )

    for li in (record.get("line_items") or [])[:12]:
        person = (li.get("person_name") or "").strip()
        if not person:
            continue
        pid = _party_id("li", person)
        amt = int(li.get("amount_gross_cents") or 0)
        parties.append(
            Party(
                id=pid,
                name=person,
                role="logistics",
                tier=3,
                amount_cents=amt,
                meta={"line_desc": li.get("description"), "corpus": "rossumai/docile"},
            )
        )
        flows.append(
            MoneyFlow(
                id=new_id("flow"),
                source_id=pid,
                target_id=vid,
                amount_cents=amt,
                kind="goods",
                doc_id=doc_id,
                memo=li.get("description") or "line party",
            )
        )

    return {"parties": parties, "flows": flows}


def ingest_docile_annotation(
    path: Path,
    *,
    store_document: bool = True,
    push_erp: bool = True,
) -> dict[str, Any]:
    record = load_annotation(path)
    doc_ref = path.stem
    profile = BIZ.upsert_from_extraction(record, doc_ref=doc_ref)

    doc_payload = None
    if store_document:
        doc_id = new_id("doc")
        summary = (
            f"DocILE {record.get('document_type')} · {record.get('vendor_name')} → "
            f"{record.get('customer_billing_name') or '—'} · "
            f"${(record.get('amount_due_cents') or 0)/100:,.2f} due · "
            f"{record.get('line_item_count', 0)} line items"
        )
        if push_erp:
            mapped = record_to_erp(record, doc_id=doc_id)
            for p in mapped["parties"]:
                ERP.upsert_party(p)
            for f in mapped["flows"]:
                ERP.add_flow(f)
            ERP.upsert_party(
                Party(id="maya-bakery", name="Maya's Bakery (HQ)", role="company", tier=4, amount_cents=0)
            )

        # lightweight catalog entry (avoid duplicating full annotation bytes for every doc)
        doc = StoredDocument(
            id=doc_id,
            filename=path.name,
            kind="scanned_financial",
            mime="application/json",
            size_bytes=path.stat().st_size if path.exists() else 0,
            stored_path=str(path),
            uploaded_at=now_iso(),
            source="docile",
            status="indexed",
            summary=summary,
            row_count=int(record.get("line_item_count") or 0),
            tags=["docile", str(record.get("document_type") or "invoice"), profile.id],
            extracted={
                "corpus": "rossumai/docile",
                "biz_id": profile.id,
                "vendor_name": record.get("vendor_name"),
                "customer": record.get("customer_billing_name"),
                "amount_due_cents": record.get("amount_due_cents"),
                "line_item_count": record.get("line_item_count"),
                "fieldtypes": list((record.get("raw_fields") or {}).keys()),
            },
        )
        ERP.documents[doc_id] = doc
        doc_payload = doc.to_dict()

    return {
        "biz_id": profile.id,
        "biz_name": profile.name,
        "document": doc_payload,
        "record": {
            "vendor_name": record.get("vendor_name"),
            "customer": record.get("customer_billing_name"),
            "amount_due_cents": record.get("amount_due_cents"),
            "line_items": record.get("line_item_count"),
            "document_type": record.get("document_type"),
        },
    }


def ingest_docile_batch(
    *,
    limit: int = 50,
    root: Path | None = None,
    push_erp: bool = True,
) -> dict[str, Any]:
    roots = [root] if root else resolve_docile_roots()
    if not roots:
        return {
            "ok": False,
            "error": f"No DocILE annotations under {DOCILE_ROOT}. Download with token and unzip.",
            "fieldtypes": fieldtype_catalog(),
        }

    ingested: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    remaining = limit
    used_root = None
    for r in roots:
        if remaining <= 0:
            break
        used_root = str(r)
        for path in iter_annotation_paths(r, limit=remaining):
            try:
                ingested.append(ingest_docile_annotation(path, push_erp=push_erp))
            except Exception as e:  # noqa: BLE001
                errors.append({"file": str(path), "error": str(e)})
            remaining -= 1
            if remaining <= 0:
                break

    BIZ.save()
    ERP.save()

    # unique businesses touched
    biz_ids = sorted({x["biz_id"] for x in ingested if x.get("biz_id")})
    return {
        "ok": True,
        "ingested": len(ingested),
        "errors": errors[:20],
        "root": used_root,
        "businesses_touched": len(biz_ids),
        "biz_ids": biz_ids[:30],
        "business_index": BIZ.list_summaries()[:20],
        "erp_totals": ERP.snapshot()["totals"],
        "fieldtypes": fieldtype_catalog(),
    }


def preview_docile(limit: int = 3) -> dict[str, Any]:
    roots = resolve_docile_roots()
    if not roots:
        return {"ok": False, "error": f"missing annotations under {DOCILE_ROOT}"}
    samples = []
    for path in iter_annotation_paths(roots[0], limit=limit):
        samples.append(load_annotation(path))
    return {
        "ok": True,
        "root": str(roots[0]),
        "available_roots": [str(r) for r in roots],
        "samples": samples,
        "fieldtypes": fieldtype_catalog(),
    }


def parse_docile_bytes(data: bytes, *, filename: str = "annotation.json") -> dict[str, Any]:
    import json

    raw = json.loads(data.decode("utf-8"))
    # accept either full annotation or already-flat record
    if "field_extractions" in raw:
        record = annotation_to_record(raw, source_path=filename)
    else:
        record = raw
        record.setdefault("corpus", "rossumai/docile")
    profile = BIZ.upsert_from_extraction(record, doc_ref=filename)
    BIZ.save()
    doc_id = new_id("doc")
    mapped = record_to_erp(record, doc_id=doc_id)
    for p in mapped["parties"]:
        ERP.upsert_party(p)
    for f in mapped["flows"]:
        ERP.add_flow(f)
    ERP.save()
    return {
        "biz_id": profile.id,
        "profile": profile.to_dict(),
        "record": record,
        "erp": {"parties": len(mapped["parties"]), "flows": len(mapped["flows"])},
    }
