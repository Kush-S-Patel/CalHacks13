"""Classify financial documents using FinDoc class priors + keyword scores."""

from __future__ import annotations

from erp.intake.taxonomy import CLASS_KEYWORDS, FINDOC_CLASSES, erp_kind_for_class


def classify_text(text: str, hinted_class: str | None = None) -> dict:
    lower = (text or "").lower()
    scores: dict[str, float] = {c: 0.0 for c in FINDOC_CLASSES}

    if hinted_class and hinted_class in scores:
        scores[hinted_class] += 5.0

    for cls, kws in CLASS_KEYWORDS.items():
        for kw in kws:
            if kw in lower:
                scores[cls] += 1.5

    # Light structure cues
    if "total assets" in lower and "liabilit" in lower:
        scores["balance_sheets"] += 2.0
    if "profit before tax" in lower or "earnings per share" in lower:
        scores["income_statement"] += 2.0
    if "operating activities" in lower and "financing activities" in lower:
        scores["cash_flow"] += 2.0

    # DocILE / commercial invoice cues (KILE field language)
    docile_hits = sum(
        1
        for kw in (
            "tax invoice",
            "amount due",
            "vendor",
            "invoice number",
            "payment terms",
            "bill to",
            "ship to",
            "vat",
            "line item",
        )
        if kw in lower
    )
    invoice_like = docile_hits >= 2 or hinted_class in {"tax_invoice", "invoice", "docile"}

    best = max(scores.items(), key=lambda kv: kv[1])
    if invoice_like and best[1] < 3.0:
        doc_class = "others"
        erp_kind = "scanned_financial"
        confidence = min(0.95, 0.55 + docile_hits * 0.08)
        return {
            "doc_class": "tax_invoice",
            "erp_kind": erp_kind,
            "confidence": round(confidence, 3),
            "scores": {k: round(v, 2) for k, v in scores.items()},
            "corpus": "rossumai/docile",
            "docile_cues": docile_hits,
        }

    doc_class = best[0] if best[1] > 0 else (hinted_class or "others")
    confidence = min(0.99, 0.35 + best[1] / 12.0)
    return {
        "doc_class": doc_class,
        "erp_kind": erp_kind_for_class(doc_class),
        "confidence": round(confidence, 3),
        "scores": {k: round(v, 2) for k, v in scores.items()},
        "corpus": "daitavan/financial-documents",
    }


def classify_document(
    *,
    text: str = "",
    hinted_class: str | None = None,
    filename: str = "",
) -> dict:
    hint = hinted_class
    fn = filename.lower()
    if not hint:
        if "balance" in fn:
            hint = "balance_sheets"
        elif "income" in fn or "pnl" in fn or "p&l" in fn:
            hint = "income_statement"
        elif "cash" in fn and "flow" in fn:
            hint = "cash_flow"
        elif "note" in fn:
            hint = "notes"
    return classify_text(text, hint)