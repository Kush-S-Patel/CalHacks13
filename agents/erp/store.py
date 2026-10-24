"""Digital document vault + ERP entity store (adjacent to NetSuite / QBO / SAP)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from erp.models import (
    GLAccount,
    JournalLine,
    MoneyFlow,
    Party,
    StoredDocument,
    now_iso,
)


class ERPStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[2] / "data" / "erp_vault"
        self.docs_dir = self.root / "documents"
        self.meta_path = self.root / "catalog.json"
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        self.documents: dict[str, StoredDocument] = {}
        self.accounts: dict[str, GLAccount] = {}
        self.parties: dict[str, Party] = {}
        self.flows: dict[str, MoneyFlow] = {}
        self.journals: list[JournalLine] = []
        self.integrations = {
            "netsuite": {"status": "connected_demo", "last_sync": None},
            "quickbooks": {"status": "available", "last_sync": None},
            "stripe": {"status": "test_mode", "last_sync": None},
            "jpm_bank": {"status": "cursor_ready", "last_sync": None},
            "nessie": {
                "status": "capital_one_hackathon_api",
                "last_sync": None,
                "marker": "Powered by Capital One Nessie",
                "docs": "https://api.nessieisreal.com/",
            },
            "shopify": {"status": "available", "last_sync": None},
        }
        self._load()

    def _load(self) -> None:
        if not self.meta_path.exists():
            return
        raw = json.loads(self.meta_path.read_text(encoding="utf-8"))
        for d in raw.get("documents", []):
            self.documents[d["id"]] = StoredDocument(**d)
        for a in raw.get("accounts", []):
            self.accounts[a["code"]] = GLAccount(**a)
        for p in raw.get("parties", []):
            self.parties[p["id"]] = Party(**p)
        for f in raw.get("flows", []):
            self.flows[f["id"]] = MoneyFlow(**f)
        for j in raw.get("journals", []):
            self.journals.append(JournalLine(**j))
        if raw.get("integrations"):
            self.integrations.update(raw["integrations"])
        # ensure Nessie slot always present after older vault loads
        self.integrations.setdefault(
            "nessie",
            {
                "status": "capital_one_hackathon_api",
                "last_sync": None,
                "marker": "Powered by Capital One Nessie",
                "docs": "https://api.nessieisreal.com/",
            },
        )

    def save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": now_iso(),
            "documents": [d.to_dict() for d in self.documents.values()],
            "accounts": [a.to_dict() for a in self.accounts.values()],
            "parties": [p.to_dict() for p in self.parties.values()],
            "flows": [f.to_dict() for f in self.flows.values()],
            "journals": [j.to_dict() for j in self.journals],
            "integrations": self.integrations,
        }
        self.meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def store_file(
        self,
        *,
        doc_id: str,
        filename: str,
        mime: str,
        data: bytes,
        kind: str,
        source: str = "upload",
    ) -> StoredDocument:
        safe = filename.replace("..", "_").replace("/", "_").replace("\\", "_")
        dest = self.docs_dir / f"{doc_id}__{safe}"
        dest.write_bytes(data)
        doc = StoredDocument(
            id=doc_id,
            filename=filename,
            kind=kind,  # type: ignore[arg-type]
            mime=mime,
            size_bytes=len(data),
            stored_path=str(dest.relative_to(self.root)).replace("\\", "/"),
            uploaded_at=now_iso(),
            source=source,
            status="stored",
        )
        self.documents[doc_id] = doc
        self.save()
        return doc

    def upsert_account(self, account: GLAccount) -> None:
        existing = self.accounts.get(account.code)
        if existing:
            existing.name = account.name or existing.name
            existing.account_type = account.account_type or existing.account_type
            existing.balance_cents = account.balance_cents
        else:
            self.accounts[account.code] = account

    def upsert_party(self, party: Party) -> None:
        existing = self.parties.get(party.id)
        if existing:
            existing.amount_cents = max(existing.amount_cents, party.amount_cents)
            existing.meta = {**existing.meta, **party.meta}
            if party.tier:
                existing.tier = party.tier
        else:
            self.parties[party.id] = party

    def add_flow(self, flow: MoneyFlow) -> None:
        self.flows[flow.id] = flow

    def snapshot(self) -> dict[str, Any]:
        rev = sum(a.balance_cents for a in self.accounts.values() if a.account_type == "revenue")
        exp = sum(a.balance_cents for a in self.accounts.values() if a.account_type == "expense")
        ar = sum(p.amount_cents for p in self.parties.values() if p.role == "customer")
        ap = sum(p.amount_cents for p in self.parties.values() if p.role == "vendor")
        return {
            "documents": [d.to_dict() for d in sorted(self.documents.values(), key=lambda x: x.uploaded_at, reverse=True)],
            "accounts": [a.to_dict() for a in self.accounts.values()],
            "parties": [p.to_dict() for p in self.parties.values()],
            "flows": [f.to_dict() for f in self.flows.values()],
            "journals": [j.to_dict() for j in self.journals[-50:]],
            "integrations": self.integrations,
            "totals": {
                "documents": len(self.documents),
                "accounts": len(self.accounts),
                "parties": len(self.parties),
                "flows": len(self.flows),
                "revenue_cents": rev,
                "expense_cents": exp,
                "ar_cents": ar,
                "ap_cents": ap,
            },
            "vault_path": str(self.root),
        }

    def clear_derived(self) -> None:
        """Clear analyzed entities but keep documents on disk."""
        self.accounts.clear()
        self.parties.clear()
        self.flows.clear()
        self.journals.clear()
        self.save()


ERP = ERPStore()


def seed_sample_if_empty() -> None:
    """Copy sample workbooks into the vault on first boot."""
    if ERP.documents:
        return
    samples = Path(__file__).resolve().parents[2] / "data" / "samples"
    if not samples.exists():
        return
    from erp.ingest import ingest_bytes

    for path in sorted(samples.glob("*")):
        if path.suffix.lower() not in {".csv", ".xlsx", ".xls", ".txt", ".json"}:
            continue
        ingest_bytes(
            filename=path.name,
            data=path.read_bytes(),
            mime=_mime(path.suffix),
            kind_hint=None,
            source="sample",
        )


def _mime(suffix: str) -> str:
    return {
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".txt": "text/plain",
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
    }.get(suffix.lower(), "application/octet-stream")