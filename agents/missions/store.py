"""Persist missions under data/erp_vault/missions/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from missions.models import EvidenceItem, Mission, MissionBudget, ToolCharge, now_iso


class MissionStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[2] / "data" / "erp_vault" / "missions"
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self.missions: dict[str, Mission] = {}
        self._load()

    def _load(self) -> None:
        for path in self.root.glob("mission-*.json"):
            raw = json.loads(path.read_text(encoding="utf-8"))
            m = self._from_dict(raw)
            self.missions[m.id] = m

    @staticmethod
    def _from_dict(raw: dict[str, Any]) -> Mission:
        b = raw.get("budget") or {}
        budget = MissionBudget(
            max_spend_cents=int(b.get("max_spend_cents") or 0),
            spent_cents=int(b.get("spent_cents") or 0),
            reserved_cents=int(b.get("reserved_cents") or 0),
        )
        charges = [ToolCharge(**c) for c in raw.get("charges") or []]
        denials = [ToolCharge(**d) for d in raw.get("denials") or []]
        evidence = [EvidenceItem(**e) for e in raw.get("evidence") or []]
        return Mission(
            id=raw["id"],
            client=raw.get("client") or "",
            brief=raw.get("brief") or "",
            quote_cents=int(raw.get("quote_cents") or 0),
            budget=budget,
            status=raw.get("status") or "draft",  # type: ignore[arg-type]
            created_at=raw.get("created_at") or now_iso(),
            updated_at=raw.get("updated_at") or now_iso(),
            charges=charges,
            denials=denials,
            evidence=evidence,
            deliverable_md=raw.get("deliverable_md") or "",
            exceptions=list(raw.get("exceptions") or []),
            work_item_ids=list(raw.get("work_item_ids") or []),
            log=list(raw.get("log") or []),
            meta=dict(raw.get("meta") or {}),
        )

    def save(self, mission: Mission | None = None) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        targets = [mission] if mission else list(self.missions.values())
        for m in targets:
            if m:
                self.missions[m.id] = m
                path = self.root / f"{m.id}.json"
                path.write_text(json.dumps(m.to_dict(), indent=2), encoding="utf-8")
        index = {
            "updated_at": now_iso(),
            "missions": [
                {
                    "id": m.id,
                    "client": m.client,
                    "status": m.status,
                    "quote_cents": m.quote_cents,
                    "spent_cents": m.budget.spent_cents,
                    "max_spend_cents": m.budget.max_spend_cents,
                    "margin_cents": m.quote_cents - m.budget.spent_cents,
                }
                for m in sorted(self.missions.values(), key=lambda x: x.created_at, reverse=True)
            ],
        }
        self.index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    def get(self, mission_id: str) -> Mission | None:
        return self.missions.get(mission_id)

    def upsert(self, mission: Mission) -> Mission:
        mission.updated_at = now_iso()
        self.missions[mission.id] = mission
        self.save(mission)
        return mission

    def list_summaries(self) -> list[dict[str, Any]]:
        return [
            {
                "id": m.id,
                "client": m.client,
                "brief": m.brief[:120],
                "status": m.status,
                "quote_cents": m.quote_cents,
                "max_spend_cents": m.budget.max_spend_cents,
                "spent_cents": m.budget.spent_cents,
                "margin_cents": m.quote_cents - m.budget.spent_cents,
                "denial_count": len(m.denials),
                "evidence_count": len(m.evidence),
                "created_at": m.created_at,
            }
            for m in sorted(self.missions.values(), key=lambda x: x.created_at, reverse=True)
        ]


MISSIONS = MissionStore()
