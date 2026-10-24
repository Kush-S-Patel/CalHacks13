"""Domain objects for the system of work (not the systems of record)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

ResourceKind = Literal[
    "work_item",
    "policy",
    "precedent",
    "forecast",
    "ledger",
    "bank",
]

WorkKind = Literal[
    "cash_match",  # bank line ↔ invoice (short wire, overpay, split)
    "ap_invoice",  # payable: duplicate / anomaly / pay
    "ar_collect",  # receivable chase
    "procurement",  # supplier price / counter
    "spend_hold",  # above-autonomy payment
    "forecast",  # runway / defer
    "policy",  # policy proposal as work
    "mission_run",  # Mission Margin Controller — budgeted job
    "budget_expand",  # human expands mission tool budget
    "mission_deliverable",  # packaged report + job ledger
    "claim_prepare",  # nonprofit reimbursement package
    "claim_risk",  # rejection-risk review hold
    "claim_question",  # ask finance manager about ambiguous expense
    "claim_policy_hold",  # next-period expense held by learned policy
]

WorkState = Literal[
    "NEW",
    "PROPOSED",
    "NEEDS_INFO",
    "BLOCKED",
    "HELD",
    "APPROVED",
    "REJECTED",
    "POSTED",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@dataclass
class Actor:
    id: str
    role: str
    display_name: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Named cast — Claims (primary) + bakery control-plane cast
SYNC = Actor("sync-job", "sync", "Sync")
AI_RISK = Actor("agent-risk", "ai_risk", "Risk / Fraud")
AI_PROCUREMENT = Actor("agent-procurement", "ai_procurement", "Procurement")
AI_COLLECTIONS = Actor("agent-collections", "ai_collections", "Collections")
AI_CASHIER = Actor("agent-cashier", "ai_cashier", "Cashier")
AI_CFO = Actor("agent-cfo", "ai_cfo", "CFO")
AI_CLAIMS = Actor("agent-claims", "ai_claims", "Claims Agent")
MAYA = Actor("human-maya", "human_owner", "Maya (Owner)")
ACCOUNTANT = Actor("human-accountant", "human_accountant", "Partner Accountant")
CONTROLLER = Actor("human-controller", "human_controller", "Controller")
FINANCE_MANAGER = Actor("human-finance-manager", "human_finance_manager", "Finance Manager")
GATEWAY = Actor("gateway", "gateway", "Gateway")

ACTORS: dict[str, Actor] = {
    a.id: a
    for a in [
        SYNC,
        AI_RISK,
        AI_PROCUREMENT,
        AI_COLLECTIONS,
        AI_CASHIER,
        AI_CFO,
        AI_CLAIMS,
        MAYA,
        ACCOUNTANT,
        CONTROLLER,
        FINANCE_MANAGER,
        GATEWAY,
    ]
}


@dataclass
class WorkItem:
    id: str
    kind: WorkKind
    state: WorkState
    subject: str  # e.g. INV-1042, JPM-wire, AR-big-cafe
    title: str
    room_id: str = "maya-bakery"
    payload: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)  # raw/golden ids
    policy_id: str | None = None
    proposed_by: str | None = None
    approved_by: str | None = None
    amount_cents: int = 0
    question: str | None = None  # ask → NEEDS_INFO
    answer: str | None = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> dict[str, Any]:
        return self.snapshot()


@dataclass
class Policy:
    """Learned rule — survives the context window (TIME)."""

    id: str
    version: int
    title: str
    rule: str  # human-readable
    condition: dict[str, Any]  # machine-checkable
    action: dict[str, Any]
    evidence: list[str]  # precedent / historical ids
    status: Literal["draft", "needs_approval", "active", "rejected"] = "needs_approval"
    proposed_by: str | None = None
    approved_by: str | None = None
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Precedent:
    """A correction or resolved case agents search next quarter."""

    id: str
    kind: str
    summary: str
    subject: str
    correction: dict[str, Any]
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    created_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditEvent:
    at: str
    actor: str
    action: str
    subject: str
    allowed: bool
    reason: str
    diff: dict[str, Any]
    evidence: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("aud"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GoldenRecord:
    """Standardised shape from Build 1 — traces to raw_ref."""

    id: str
    kind: str  # bank_transaction | invoice | vendor | customer | gl_account
    source: str
    data: dict[str, Any]
    raw_ref: str
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)