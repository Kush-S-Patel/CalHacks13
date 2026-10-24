"""
End-to-end document intake:

OCR JSON (FinDoc) / FinCriticalED HTML / uploads
  → classify → extract amounts → digital vault → ERP entities → graphs/summary
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from erp.intake.classifier import classify_document
from erp.intake.extractors import rows_to_erp_entities
from erp.intake.fincritical import default_fincritical_path, iter_fincritical_rows
from erp.intake.ocr_parse import (
    extract_labeled_amounts,
    guess_class_from_path,
    load_ocr_tokens,
    tokens_to_lines,
    tokens_to_text,
)
from erp.intake.taxonomy import erp_kind_for_class
from erp.models import GLAccount, MoneyFlow, Party, new_id
from erp.store import ERP


TRAIN_OCR_ROOT = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "train_data"
    / "accounting_samples"
    / "financial-documents"
    / "financial-documents"
    / "ocr"
)


def ingest_ocr_json(
    *,
    path: Path | None = None,
    raw: bytes | list | None = None,
    filename: str | None = None,
    hinted_class: str | None = None,
    source: str = "train_ocr",
) -> dict[str, Any]:
    if path is not None:
        tokens = load_ocr_tokens(path)
        filename = filename or path.name
        hinted_class = hinted_class or guess_class_from_path(path)
    elif raw is not None:
        tokens = load_ocr_tokens(raw)
        filename = filename or "ocr.json"
    else:
        raise ValueError("path or raw required")

    lines = tokens_to_lines(tokens)
    text = "\n".join(lines)
    classification = classify_document(text=text, hinted_class=hinted_class, filename=filename or "")
    doc_class = classification["doc_class"]
    erp_kind = classification["erp_kind"]

    labeled = extract_labeled_amounts(lines)
    doc_id = new_id("doc")
    payload = json.dumps(tokens).encode("utf-8")
    doc = ERP.store_file(
        doc_id=doc_id,
        filename=filename or f"{doc_class}.json",
        mime="application/json",
        data=payload,
        kind=erp_kind,
        source=source,
    )

    extracted = rows_to_erp_entities(
        labeled_rows=labeled,
        doc_class=doc_class,
        doc_id=doc_id,
        source_name=filename or doc_class,
    )
    for a in extracted["accounts"]:
        ERP.upsert_account(a)
    for p in extracted["parties"]:
        ERP.upsert_party(p)
    for f in extracted["flows"]:
        ERP.add_flow(f)
    ERP.upsert_party(
        Party(id="maya-bakery", name="Maya's Bakery (HQ)", role="company", tier=4, amount_cents=0)
    )

    doc.status = "indexed"
    doc.row_count = extracted["line_count"]
    doc.summary = (
        f"{doc_class} via FinDoc OCR · conf {classification['confidence']:.2f} · "
        f"{extracted['indexed_accounts']} GL lines"
    )
    doc.tags = [doc_class, erp_kind, "ocr", "findoc", source]
    doc.extracted = {
        "doc_class": doc_class,
        "confidence": classification["confidence"],
        "scores": classification["scores"],
        "preview_lines": lines[:12],
        "labeled_preview": labeled[:8],
        "corpus": "daitavan/financial-documents",
    }
    ERP.documents[doc_id] = doc
    ERP.integrations["netsuite"]["last_sync"] = doc.uploaded_at
    ERP.save()

    return {
        "document": doc.to_dict(),
        "classification": classification,
        "extraction": {
            "line_count": extracted["line_count"],
            "indexed_accounts": extracted["indexed_accounts"],
            "parties": len(extracted["parties"]),
            "flows": len(extracted["flows"]),
        },
        "erp_totals": ERP.snapshot()["totals"],
    }


def ingest_fincritical_sample(*, limit: int = 5) -> dict[str, Any]:
    path = default_fincritical_path()
    if not path.exists():
        return {"ok": False, "error": f"missing {path}"}

    ingested = []
    for row in iter_fincritical_rows(path, limit=limit):
        doc_id = new_id("doc")
        form = row["form"]
        kind = erp_kind_for_class(form if form in {"form4", "10k", "10q"} else "sec_filing")
        text = row["text"]
        doc = ERP.store_file(
            doc_id=doc_id,
            filename=f"fincritical_{row['id']}_{form}.txt",
            mime="text/plain",
            data=text.encode("utf-8"),
            kind=kind,
            source="fincritical",
        )
        classification = classify_document(text=text, filename=form)
        # SEC forms rarely yield statement lines; store as critical filing context party
        party_id = f"sec-{form}-{row['id']}"
        ERP.upsert_party(
            Party(
                id=party_id,
                name=f"SEC {form.upper()} #{row['id']}",
                role="company",
                tier=0,
                amount_cents=0,
                meta={"corpus": "TheFinAI/FinCriticalED", "html_chars": row["html_chars"]},
            )
        )
        ERP.add_flow(
            MoneyFlow(
                id=new_id("flow"),
                source_id="maya-bakery",
                target_id=party_id,
                amount_cents=0,
                kind="goods",
                doc_id=doc_id,
                memo=f"FinCriticalED {form}",
            )
        )
        doc.status = "indexed"
        doc.summary = f"FinCriticalED {form} · {len(text)} chars text extracted from matched_html"
        doc.tags = ["fincritical", form, "sec", kind]
        doc.extracted = {
            "form": form,
            "classification": classification,
            "preview": text[:500],
            "corpus": "TheFinAI/FinCriticalED",
        }
        doc.row_count = text.count("\n") + 1
        ERP.documents[doc_id] = doc
        ingested.append(doc.to_dict())

    ERP.save()
    return {"ok": True, "ingested": len(ingested), "documents": ingested, "totals": ERP.snapshot()["totals"]}


def ingest_train_batch(
    *,
    per_class: int = 3,
    include_fincritical: bool = True,
    fincritical_limit: int = 3,
) -> dict[str, Any]:
    """Bootstrap vault from local train_data mirrors of HF datasets."""
    results: list[dict[str, Any]] = []
    if TRAIN_OCR_ROOT.exists():
        for cls_dir in sorted(TRAIN_OCR_ROOT.iterdir()):
            if not cls_dir.is_dir():
                continue
            files = sorted(cls_dir.glob("*.json"))[:per_class]
            for f in files:
                try:
                    results.append(ingest_ocr_json(path=f, hinted_class=cls_dir.name, source="train_ocr"))
                except Exception as e:  # noqa: BLE001
                    results.append({"error": str(e), "file": str(f)})

    fc = None
    if include_fincritical:
        fc = ingest_fincritical_sample(limit=fincritical_limit)

    return {
        "ocr_ingested": sum(1 for r in results if "document" in r),
        "ocr_errors": [r for r in results if "error" in r],
        "fincritical": fc,
        "totals": ERP.snapshot()["totals"],
        "train_ocr_root": str(TRAIN_OCR_ROOT),
    }


# re-export
__all__ = [
    "classify_document",
    "ingest_ocr_json",
    "ingest_fincritical_sample",
    "ingest_train_batch",
]