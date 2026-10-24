"""ERP-shaped entities that sit beside systems of record (NetSuite / QuickBooks / SAP)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


DocKind = Literal[
    "chart_of_accounts",
    "revenue",
    "ap_aging",
    "ar_aging",
    "bank",
    "supply_chain",
    "payroll",
    "scanned_financial",
    "journal",
    "other",
]


@dataclass
class StoredDocument:
    id: str
    filename: str
    kind: DocKind
    mime: str
    size_bytes: int
    stored_path: str
    uploaded_at: str
    source: str = "upload"  # upload | scan | erp_sync | sample
    status: str = "stored"  # stored | analyzing | indexed | error
    summary: str = ""
    row_count: int = 0
    extracted: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GLAccount:
    code: str
    name: str
    account_type: str  # asset | liability | equity | revenue | expense
    balance_cents: int = 0
    entity: str = "maya-bakery"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Party:
    id: str
    name: str
    role: str  # vendor | customer | logistics | site | origin
    tier: int = 0
    amount_cents: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MoneyFlow:
    id: str
    source_id: str
    target_id: str
    amount_cents: int
    kind: str  # revenue | payable | receivable | transfer | goods
    doc_id: str | None = None
    fraud: bool = False
    memo: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class JournalLine:
    id: str
    account_code: str
    debit_cents: int
    credit_cents: int
    memo: str
    doc_id: str | None = None
    posted_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)