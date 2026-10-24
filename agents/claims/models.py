"""Nonprofit reimbursement claim package models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


ClaimStatus = Literal[
    "draft",
    "analyzing",
    "exceptions",
    "ready_for_approval",
    "approved",
    "rejected_prediction",  # high risk — do not submit
]


@dataclass
class AwardRulebook:
    award_id: str
    funder: str
    cfda: str
    period_start: str
    period_end: str
    budget_lines: dict[str, int]  # category → cents
    required_docs: list[str]
    notes: str = ""
    source_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TxMatch:
    id: str
    ledger_id: str
    description: str
    amount_cents: int
    date: str
    vendor: str
    budget_line: str
    evidence_ids: list[str]
    confidence: float
    exception_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceDoc:
    id: str
    kind: str  # receipt | invoice | payroll | timesheet | other
    filename: str
    linked_ledger_id: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskScore:
    score: int  # 0–100 higher = more likely to face rejection/findings
    band: Literal["low", "moderate", "high", "critical"]
    drivers: list[dict[str, Any]]
    corpus_priors: dict[str, Any]
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClaimPackage:
    id: str
    nonprofit: str
    award: AwardRulebook
    reporting_period: str
    status: ClaimStatus = "draft"
    matches: list[TxMatch] = field(default_factory=list)
    evidence: list[EvidenceDoc] = field(default_factory=list)
    exceptions: list[dict[str, Any]] = field(default_factory=list)
    risk: RiskScore | None = None
    totals: dict[str, int] = field(default_factory=dict)
    schedules_md: str = ""
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    work_item_ids: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nonprofit": self.nonprofit,
            "award": self.award.to_dict(),
            "reporting_period": self.reporting_period,
            "status": self.status,
            "matches": [m.to_dict() for m in self.matches],
            "evidence": [e.to_dict() for e in self.evidence],
            "exceptions": self.exceptions,
            "risk": self.risk.to_dict() if self.risk else None,
            "totals": self.totals,
            "schedules_md": self.schedules_md,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "work_item_ids": self.work_item_ids,
            "log": self.log,
            "meta": self.meta,
        }
