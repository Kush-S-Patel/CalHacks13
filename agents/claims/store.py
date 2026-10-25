"""Persist claim packages under data/erp_vault/claims/."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from claims.models import (
    AwardRulebook,
    ClaimPackage,
    EvidenceDoc,
    RiskScore,
    TxMatch,
    now_iso,
)


class ClaimStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else Path(
            os.getenv("SWARMCFO_CLAIMS_DIR")
            or str(Path(__file__).resolve().parents[2] / "data" / "erp_vault" / "claims")
        )
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self.packages: dict[str, ClaimPackage] = {}
        self._load()

    def _load(self) -> None:
        for path in self.root.glob("claim-*.json"):
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.packages[raw["id"]] = self._from_dict(raw)

    @staticmethod
    def _from_dict(raw: dict[str, Any]) -> ClaimPackage:
        award = AwardRulebook(**raw["award"])
        matches = [TxMatch(**m) for m in raw.get("matches") or []]
        evidence = [EvidenceDoc(**e) for e in raw.get("evidence") or []]
        risk = RiskScore(**raw["risk"]) if raw.get("risk") else None
        return ClaimPackage(
            id=raw["id"],
            nonprofit=raw.get("nonprofit") or "",
            award=award,
            reporting_period=raw.get("reporting_period") or "",
            status=raw.get("status") or "draft",  # type: ignore[arg-type]
            matches=matches,
            evidence=evidence,
            exceptions=list(raw.get("exceptions") or []),
            risk=risk,
            totals=dict(raw.get("totals") or {}),
            schedules_md=raw.get("schedules_md") or "",
            created_at=raw.get("created_at") or now_iso(),
            updated_at=raw.get("updated_at") or now_iso(),
            work_item_ids=list(raw.get("work_item_ids") or []),
            log=list(raw.get("log") or []),
            meta=dict(raw.get("meta") or {}),
        )

    def upsert(self, package: ClaimPackage) -> ClaimPackage:
        package.updated_at = now_iso()
        self.packages[package.id] = package
        path = self.root / f"{package.id}.json"
        path.write_text(json.dumps(package.to_dict(), indent=2), encoding="utf-8")
        index = {
            "updated_at": now_iso(),
            "claims": [
                {
                    "id": p.id,
                    "nonprofit": p.nonprofit,
                    "period": p.reporting_period,
                    "status": p.status,
                    "risk_score": p.risk.score if p.risk else None,
                    "risk_band": p.risk.band if p.risk else None,
                    "claimed_cents": (p.totals or {}).get("claimed_cents"),
                }
                for p in sorted(self.packages.values(), key=lambda x: x.created_at, reverse=True)
            ],
        }
        self.index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
        return package

    def get(self, claim_id: str) -> ClaimPackage | None:
        return self.packages.get(claim_id)

    def list_summaries(self) -> list[dict[str, Any]]:
        return [
            {
                "id": p.id,
                "nonprofit": p.nonprofit,
                "award_id": p.award.award_id,
                "period": p.reporting_period,
                "status": p.status,
                "risk_score": p.risk.score if p.risk else None,
                "risk_band": p.risk.band if p.risk else None,
                "claimed_cents": (p.totals or {}).get("claimed_cents", 0),
                "exception_count": len(p.exceptions),
                "match_count": len(p.matches),
            }
            for p in sorted(self.packages.values(), key=lambda x: x.created_at, reverse=True)
        ]


CLAIMS = ClaimStore()
