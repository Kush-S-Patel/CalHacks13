"""Mission Margin Controller domain objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


MissionStatus = Literal[
    "draft",
    "running",
    "held",  # budget exhausted — needs expand or stop
    "completed",
    "stopped",
    "failed",
]


@dataclass
class ToolCharge:
    id: str
    at: str
    agent: str
    tool: str
    amount_cents: int
    allowed: bool
    reason: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceItem:
    id: str
    source: str
    claim: str
    confidence: float
    agent: str
    url_or_ref: str = ""
    verified: bool | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MissionBudget:
    max_spend_cents: int
    spent_cents: int = 0
    reserved_cents: int = 0

    @property
    def remaining_cents(self) -> int:
        return max(0, self.max_spend_cents - self.spent_cents - self.reserved_cents)

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_spend_cents": self.max_spend_cents,
            "spent_cents": self.spent_cents,
            "reserved_cents": self.reserved_cents,
            "remaining_cents": self.remaining_cents,
        }


@dataclass
class Mission:
    id: str
    client: str
    brief: str
    quote_cents: int
    budget: MissionBudget
    status: MissionStatus = "draft"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    charges: list[ToolCharge] = field(default_factory=list)
    denials: list[ToolCharge] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)
    deliverable_md: str = ""
    exceptions: list[str] = field(default_factory=list)
    work_item_ids: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def job_ledger(self) -> dict[str, Any]:
        spend = self.budget.spent_cents
        margin = self.quote_cents - spend
        by_agent: dict[str, int] = {}
        by_tool: dict[str, int] = {}
        for c in self.charges:
            if not c.allowed:
                continue
            by_agent[c.agent] = by_agent.get(c.agent, 0) + c.amount_cents
            by_tool[c.tool] = by_tool.get(c.tool, 0) + c.amount_cents
        return {
            "mission_id": self.id,
            "client": self.client,
            "status": self.status,
            "quote_cents": self.quote_cents,
            "max_spend_cents": self.budget.max_spend_cents,
            "spent_cents": spend,
            "remaining_cents": self.budget.remaining_cents,
            "margin_cents": margin,
            "margin_pct": round(100.0 * margin / self.quote_cents, 2) if self.quote_cents else 0.0,
            "by_agent_cents": by_agent,
            "by_tool_cents": by_tool,
            "charge_count": len(self.charges),
            "denial_count": len(self.denials),
            "evidence_count": len(self.evidence),
            "exception_count": len(self.exceptions),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "client": self.client,
            "brief": self.brief,
            "quote_cents": self.quote_cents,
            "budget": self.budget.to_dict(),
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "charges": [c.to_dict() for c in self.charges],
            "denials": [d.to_dict() for d in self.denials],
            "evidence": [e.to_dict() for e in self.evidence],
            "deliverable_md": self.deliverable_md,
            "exceptions": self.exceptions,
            "work_item_ids": self.work_item_ids,
            "log": self.log,
            "meta": self.meta,
            "job_ledger": self.job_ledger(),
        }


# Deterministic tool price list (cents) — invariants in code, not LLM
TOOL_PRICES_CENTS: dict[str, int] = {
    "web_search": 25,  # $0.25
    "extract_facts": 10,  # $0.10
    "verify_claim": 15,  # $0.15
    "claude_turn": 0,  # computed from tokens
    "compose_report": 5,  # $0.05
}

# Rough token rates (cents per 1k tokens) for mission metering
CLAUDE_INPUT_CENTS_PER_1K = 3  # ~$0.003 / 1k
CLAUDE_OUTPUT_CENTS_PER_1K = 15  # ~$0.015 / 1k
