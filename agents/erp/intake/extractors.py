"""Map OCR-extracted statement lines into ERP GL / party / flow entities."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from erp.models import GLAccount, MoneyFlow, Party, new_id


def _code_for_label(label: str, prefix: str) -> str:
    h = hashlib.md5(label.lower().encode(), usedforsecurity=False).hexdigest()[:4]
    slug = re.sub(r"[^A-Z0-9]", "", label.upper())[:8] or "LINE"
    return f"{prefix}-{slug}-{h}"


def _account_type(label: str, doc_class: str) -> str:
    l = label.lower()
    if any(k in l for k in ("liabilit", "payable", "borrow", "debt", "provision")):
        return "liability"
    if any(k in l for k in ("equity", "capital", "reserve", "surplus")):
        return "equity"
    if doc_class == "income_statement":
        if any(k in l for k in ("expense", "cost", "depreciation", "tax expense", "finance cost")):
            return "expense"
        if any(k in l for k in ("revenue", "income", "sales", "profit")):
            return "revenue"
        return "revenue"
    if any(k in l for k in ("cash", "bank", "receivable", "inventory", "asset", "deposit")):
        return "asset"
    if doc_class == "cash_flow":
        return "asset"
    return "asset"


def rows_to_erp_entities(
    *,
    labeled_rows: list[dict[str, Any]],
    doc_class: str,
    doc_id: str,
    source_name: str,
) -> dict[str, Any]:
    accounts: list[GLAccount] = []
    parties: list[Party] = []
    flows: list[MoneyFlow] = []

    prefix = {
        "balance_sheets": "BS",
        "income_statement": "IS",
        "cash_flow": "CF",
        "notes": "NT",
        "others": "DOC",
    }.get(doc_class, "DOC")

    for row in labeled_rows[:80]:
        label = row["label"]
        amt = int(row["amount_cents"])
        code = _code_for_label(label, prefix)
        atype = _account_type(label, doc_class)
        accounts.append(
            GLAccount(
                code=code,
                name=label[:80],
                account_type=atype,
                balance_cents=amt,
            )
        )

        # Material counterparties mentioned in notes/others become parties
        if doc_class in {"notes", "others", "income_statement"}:
            if any(k in label.lower() for k in ("customer", "vendor", "supplier", "debtor", "creditor")):
                pid = f"party-{code.lower()}"
                parties.append(
                    Party(
                        id=pid,
                        name=label[:60],
                        role="customer" if "debtor" in label.lower() or "customer" in label.lower() else "vendor",
                        amount_cents=abs(amt),
                        meta={"from_doc": source_name, "doc_class": doc_class},
                    )
                )
                flows.append(
                    MoneyFlow(
                        id=new_id("flow"),
                        source_id=pid if "customer" in label.lower() else "maya-bakery",
                        target_id="maya-bakery" if "customer" in label.lower() else pid,
                        amount_cents=abs(amt),
                        kind="receivable" if "customer" in label.lower() else "payable",
                        doc_id=doc_id,
                        memo=label[:80],
                    )
                )

    # Always link statement rollups into a context flow from company hub
    if accounts:
        top = max(accounts, key=lambda a: abs(a.balance_cents))
        flows.append(
            MoneyFlow(
                id=new_id("flow"),
                source_id="maya-bakery",
                target_id=f"stmt-{doc_class}",
                amount_cents=abs(top.balance_cents),
                kind="goods" if doc_class == "balance_sheets" else "revenue",
                doc_id=doc_id,
                memo=f"{doc_class}: {top.name}",
            )
        )
        parties.append(
            Party(
                id=f"stmt-{doc_class}",
                name=doc_class.replace("_", " ").title(),
                role="company",
                tier=4,
                amount_cents=abs(top.balance_cents),
                meta={"statement": doc_class, "source": source_name},
            )
        )

    return {
        "accounts": accounts,
        "parties": parties,
        "flows": flows,
        "line_count": len(labeled_rows),
        "indexed_accounts": len(accounts),
    }