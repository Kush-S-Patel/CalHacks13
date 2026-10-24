"""
DocILE annotation → structured invoice record.

Field taxonomy (KILE + LIR) mirrors rossumai/docile:
  vendor_*, customer_*, amount_*, date_*, order_*, payment_*, line_item_*
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


DOCILE_ROOT = Path(__file__).resolve().parents[3] / "data" / "train_data" / "docile"

# Prefer synthetic chunk (present after download); annotated-trainval when unzipped.
PREFERRED_SPLITS = (
    "synthetic-chunk-0",
    "annotated-trainval",
    "train",
    "val",
)


def _money_to_cents(text: str | None) -> int:
    if not text:
        return 0
    s = str(text).replace(",", "").replace(" ", "")
    # strip currency codes / symbols
    s = re.sub(r"[^0-9.\-]", "", s)
    if not s or s in {".", "-", "-."}:
        return 0
    try:
        return int(round(float(s) * 100))
    except ValueError:
        return 0


def _qty(text: str | None) -> float:
    if not text:
        return 0.0
    s = re.sub(r"[^0-9.\-]", "", str(text).replace(",", ""))
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def fields_map(extractions: list[dict[str, Any]]) -> dict[str, str]:
    """First-wins map fieldtype → text (DocILE may repeat keys)."""
    out: dict[str, str] = {}
    for f in extractions or []:
        ft = f.get("fieldtype")
        if not ft or ft in out:
            continue
        t = f.get("text")
        if t is None:
            continue
        out[ft] = str(t).strip()
    return out


def group_line_items(extractions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[int, dict[str, Any]] = {}
    for f in extractions or []:
        li_id = f.get("line_item_id")
        if li_id is None:
            continue
        try:
            lid = int(li_id)
        except (TypeError, ValueError):
            continue
        if lid <= 0:
            continue  # headers use 0
        row = by_id.setdefault(lid, {"line_item_id": lid})
        ft = f.get("fieldtype") or ""
        text = str(f.get("text") or "").strip()
        if ft == "line_item_description":
            row["description"] = text
        elif ft == "line_item_code":
            row["code"] = text
        elif ft == "line_item_quantity":
            row["quantity"] = _qty(text)
            row["quantity_raw"] = text
        elif ft == "line_item_amount_gross":
            row["amount_gross_cents"] = _money_to_cents(text)
            row["amount_gross_raw"] = text
        elif ft == "line_item_unit_price_gross":
            row["unit_price_cents"] = _money_to_cents(text)
        elif ft == "line_item_date":
            row["date"] = text
        elif ft == "line_item_person_name":
            row["person_name"] = text
        elif ft == "line_item_units_of_measure":
            row["uom"] = text
        else:
            row[ft] = text
    return [by_id[k] for k in sorted(by_id)]


def annotation_to_record(raw: dict[str, Any], *, source_path: str | None = None) -> dict[str, Any]:
    fields = fields_map(raw.get("field_extractions") or [])
    meta = raw.get("metadata") or {}
    line_items = group_line_items(raw.get("line_item_extractions") or [])

    currency = (
        meta.get("currency")
        or fields.get("currency_code_amount_due")
        or ""
    )
    if currency in {"$", "USD$", "US$"}:
        currency = "USD"

    record = {
        "corpus": "rossumai/docile",
        "source_path": source_path,
        "document_type": meta.get("document_type") or "tax_invoice",
        "language": meta.get("language"),
        "cluster_id": meta.get("cluster_id"),
        "currency": currency,
        "vendor_name": fields.get("vendor_name"),
        "vendor_tax_id": fields.get("vendor_tax_id"),
        "vendor_address": fields.get("vendor_address"),
        "customer_billing_name": fields.get("customer_billing_name"),
        "customer_billing_address": fields.get("customer_billing_address"),
        "customer_delivery_name": fields.get("customer_delivery_name"),
        "customer_delivery_address": fields.get("customer_delivery_address"),
        "customer_id": fields.get("customer_id"),
        "document_id": fields.get("document_id"),
        "order_id": fields.get("order_id"),
        "customer_order_id": fields.get("customer_order_id"),
        "date_issue": fields.get("date_issue"),
        "date_due": fields.get("date_due"),
        "payment_terms": fields.get("payment_terms"),
        "payment_reference": fields.get("payment_reference"),
        "account_num": fields.get("account_num"),
        "amount_total_gross": fields.get("amount_total_gross"),
        "amount_due": fields.get("amount_due"),
        "amount_total_gross_cents": _money_to_cents(fields.get("amount_total_gross")),
        "amount_due_cents": _money_to_cents(fields.get("amount_due")),
        "raw_fields": fields,
        "line_items": line_items,
        "line_item_count": len(line_items),
    }
    return record


def load_annotation(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return annotation_to_record(raw, source_path=str(path))


def resolve_docile_roots() -> list[Path]:
    roots: list[Path] = []
    if not DOCILE_ROOT.exists():
        return roots
    for name in PREFERRED_SPLITS:
        p = DOCILE_ROOT / name
        ann = p / "annotations"
        if ann.is_dir():
            roots.append(p)
    # any other */annotations
    for p in sorted(DOCILE_ROOT.iterdir()):
        if p.is_dir() and (p / "annotations").is_dir() and p not in roots:
            roots.append(p)
    return roots


def iter_annotation_paths(root: Path, *, limit: int | None = None) -> Iterable[Path]:
    ann = root / "annotations"
    paths = sorted(ann.glob("*.json"))
    if limit is not None:
        paths = paths[:limit]
    return paths


def fieldtype_catalog() -> dict[str, list[str]]:
    """Stable DocILE fieldtypes used to improve extraction prompts / classifiers."""
    return {
        "kile": [
            "vendor_name",
            "vendor_tax_id",
            "vendor_address",
            "customer_billing_name",
            "customer_billing_address",
            "customer_delivery_name",
            "customer_delivery_address",
            "customer_id",
            "document_id",
            "order_id",
            "customer_order_id",
            "date_issue",
            "date_due",
            "amount_total_gross",
            "amount_due",
            "currency_code_amount_due",
            "payment_terms",
            "payment_reference",
            "account_num",
        ],
        "lir": [
            "line_item_description",
            "line_item_code",
            "line_item_quantity",
            "line_item_amount_gross",
            "line_item_unit_price_gross",
            "line_item_date",
            "line_item_person_name",
            "line_item_units_of_measure",
        ],
    }
