"""Document intake — FinDoc OCR + FinCriticalED + DocILE → ERP vault."""

from erp.intake.docile_ingest import ingest_docile_batch
from erp.intake.pipeline import classify_document, ingest_ocr_json, ingest_train_batch

__all__ = [
    "classify_document",
    "ingest_ocr_json",
    "ingest_train_batch",
    "ingest_docile_batch",
]