"""Ingest uploads into the digital vault and run spreadsheet analysis."""

from __future__ import annotations

from typing import Any

from erp.analyzer import (
    analyze_rows,
    detect_kind,
    rows_from_csv_bytes,
    rows_from_scanned_text,
    rows_from_xlsx_bytes,
)
from erp.models import GLAccount, JournalLine, MoneyFlow, Party, new_id
from erp.store import ERP


def ingest_bytes(
    *,
    filename: str,
    data: bytes,
    mime: str = "application/octet-stream",
    kind_hint: str | None = None,
    source: str = "upload",
    scan_text: str | None = None,
) -> dict[str, Any]:
    doc_id = new_id("doc")
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    headers: list[str] = []
    rows: list[list[Any]] = []
    parse_error: str | None = None

    try:
        if scan_text:
            headers, rows = rows_from_scanned_text(scan_text)
            kind_hint = kind_hint or "scanned_financial"
        elif ext in {"csv", "txt"} or "csv" in mime:
            headers, rows = rows_from_csv_bytes(data)
        elif ext in {"xlsx", "xlsm"} or "spreadsheet" in mime or "excel" in mime:
            headers, rows = rows_from_xlsx_bytes(data)
        elif ext == "json":
            import json

            payload = json.loads(data.decode("utf-8"))
            # FinDoc OCR token list → dedicated intake pipeline
            if (
                isinstance(payload, list)
                and payload
                and isinstance(payload[0], dict)
                and "word" in payload[0]
                and "bounding_box" in payload[0]
            ):
                from erp.intake.pipeline import ingest_ocr_json

                return ingest_ocr_json(
                    raw=payload,
                    filename=filename,
                    hinted_class=kind_hint,
                    source=source,
                )
            if isinstance(payload, list) and payload and isinstance(payload[0], dict):
                headers = list(payload[0].keys())
                rows = [[r.get(h) for h in headers] for r in payload]
            else:
                parse_error = "JSON must be OCR tokens or an array of objects"
        elif ext in {"png", "jpg", "jpeg", "webp", "pdf"}:
            # Store digitally; analysis needs OCR text — accept empty until scan_text provided
            kind_hint = kind_hint or "scanned_financial"
            parse_error = None
            headers, rows = [], []
        else:
            # Try CSV decode as last resort
            try:
                headers, rows = rows_from_csv_bytes(data)
            except Exception as e:  # noqa: BLE001
                parse_error = str(e)
    except Exception as e:  # noqa: BLE001
        parse_error = str(e)

    kind = kind_hint or (detect_kind(filename, headers) if headers else "other")
    doc = ERP.store_file(
        doc_id=doc_id,
        filename=filename,
        mime=mime,
        data=data if data else (scan_text or "").encode(),
        kind=kind,
        source=source,
    )

    analysis: dict[str, Any] = {
        "kind": kind,
        "headers": headers,
        "mapped_columns": {},
        "row_count": len(rows),
        "accounts": [],
        "parties": [],
        "flows": [],
        "journals": [],
        "notes": [],
        "preview_rows": [],
    }

    if headers and rows:
        doc.status = "analyzing"
        analysis = analyze_rows(filename=filename, headers=headers, rows=rows, kind_hint=kind)
        _apply_analysis(doc_id, analysis)
        doc.status = "indexed"
        doc.row_count = analysis["row_count"]
        doc.summary = "; ".join(analysis.get("notes") or [f"Indexed as {analysis['kind']}"])
        doc.extracted = {
            "mapped_columns": analysis.get("mapped_columns"),
            "preview_rows": analysis.get("preview_rows"),
            "kind": analysis.get("kind"),
        }
        doc.kind = analysis["kind"]  # type: ignore[assignment]
        doc.tags = [analysis["kind"], "erp", source]
    elif ext in {"png", "jpg", "jpeg", "webp", "pdf"}:
        doc.status = "stored"
        doc.summary = "Scanned financial stored digitally. Paste OCR text or re-upload CSV/XLSX to analyze."
        doc.tags = ["scanned_financial", "pending_ocr"]
    else:
        doc.status = "error" if parse_error else "stored"
        doc.summary = parse_error or "Stored without tabular rows"
        doc.tags = [kind, source]

    ERP.documents[doc_id] = doc
    ERP.integrations["netsuite"]["last_sync"] = doc.uploaded_at
    ERP.save()

    return {
        "document": doc.to_dict(),
        "analysis": analysis,
        "erp_totals": ERP.snapshot()["totals"],
        "parse_error": parse_error,
    }


def _apply_analysis(doc_id: str, analysis: dict[str, Any]) -> None:
    for a in analysis.get("accounts", []):
        ERP.upsert_account(GLAccount(**a))
    for p in analysis.get("parties", []):
        ERP.upsert_party(Party(**p))
    for f in analysis.get("flows", []):
        f = dict(f)
        f["doc_id"] = doc_id
        ERP.add_flow(MoneyFlow(**f))
    for j in analysis.get("journals", []):
        j = dict(j)
        j["doc_id"] = doc_id
        ERP.journals.append(JournalLine(**j))
    # Ensure company hub exists for graphs
    ERP.upsert_party(
        Party(id="maya-bakery", name="Maya's Bakery (HQ)", role="company", tier=4, amount_cents=0)
    )


def reanalyze_document(doc_id: str, scan_text: str | None = None) -> dict[str, Any]:
    doc = ERP.documents.get(doc_id)
    if not doc:
        raise KeyError(doc_id)
    path = ERP.root / doc.stored_path
    data = path.read_bytes() if path.exists() else b""
    # Remove old flows tied to this doc
    ERP.flows = {k: v for k, v in ERP.flows.items() if v.doc_id != doc_id}
    return ingest_bytes(
        filename=doc.filename,
        data=data,
        mime=doc.mime,
        kind_hint=doc.kind,
        source=doc.source,
        scan_text=scan_text,
    )