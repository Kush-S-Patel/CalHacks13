"""
Document taxonomy aligned to training corpora:

- daitavan/financial-documents — image OCR classes
  https://huggingface.co/datasets/daitavan/financial-documents
- TheFinAI/FinCriticalED — critical SEC / financial HTML+scan pairs
  https://huggingface.co/datasets/TheFinAI/FinCriticalED
"""

from __future__ import annotations

# Folder / label names in data/train_data/.../ocr/
FINDOC_CLASSES = (
    "balance_sheets",
    "cash_flow",
    "income_statement",
    "notes",
    "others",
)

# Map vision/OCR class → ERP DocKind used by the vault
CLASS_TO_ERP_KIND: dict[str, str] = {
    "balance_sheets": "chart_of_accounts",
    "cash_flow": "bank",
    "income_statement": "revenue",
    "notes": "scanned_financial",
    "others": "scanned_financial",
    # FinCriticalED-ish / SEC
    "sec_form": "scanned_financial",
    "sec_filing": "scanned_financial",
    "10k": "scanned_financial",
    "10q": "scanned_financial",
    "form4": "scanned_financial",
}

# Keywords that boost classification when folder label is missing
CLASS_KEYWORDS: dict[str, tuple[str, ...]] = {
    "balance_sheets": (
        "balance sheet",
        "assets",
        "liabilities",
        "equity",
        "shareholders",
        "non-current assets",
        "current assets",
        "total assets",
    ),
    "income_statement": (
        "profit and loss",
        "statement of profit",
        "income statement",
        "revenue from operations",
        "total income",
        "profit before tax",
        "earnings per share",
        "comprehensive income",
    ),
    "cash_flow": (
        "cash flow",
        "cash flows",
        "operating activities",
        "investing activities",
        "financing activities",
        "net increase in cash",
    ),
    "notes": (
        "notes to",
        "significant accounting",
        "contingent",
        "related party",
        "fair value hierarchy",
    ),
}


def erp_kind_for_class(doc_class: str) -> str:
    return CLASS_TO_ERP_KIND.get(doc_class, "scanned_financial")