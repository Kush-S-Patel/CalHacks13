"""
NetSuite-adjacent SoR adapter.

Gateway posts become Vendor / VendorBill / Customer / Invoice / Payment /
JournalEntry records (SuiteTalk-shaped), persisted under data/erp_vault/netsuite.json
and mirrored into the ERP vault (parties, journals, flows).

Optional live SuiteTalk: set NETSUITE_ACCOUNT_ID + NETSUITE_TOKEN_* in .env
(when absent we run the faithful local mirror used by the demo).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from erp.models import GLAccount, JournalLine, MoneyFlow, Party, new_id, now_iso
from erp.store import ERP

log = logging.getLogger("swarmcfo.netsuite")

STATE_PATH = Path(__file__).resolve().parents[3] / "data" / "erp_vault" / "netsuite.json"


class NetSuiteAdapter:
    def __init__(self) -> None:
        self.vendors: dict[str, dict[str, Any]] = {}
        self.customers: dict[str, dict[str, Any]] = {}
        self.vendor_bills: dict[str, dict[str, Any]] = {}
        self.invoices: dict[str, dict[str, Any]] = {}
        self.payments: dict[str, dict[str, Any]] = {}
        self.journal_entries: dict[str, dict[str, Any]] = {}
        self.fraud_flags: list[dict[str, Any]] = []
        self.last_sync: str | None = None
        self._load()

    def _load(self) -> None:
        if not STATE_PATH.exists():
            return
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        self.vendors = {v["id"]: v for v in raw.get("vendors", [])}
        self.customers = {c["id"]: c for c in raw.get("customers", [])}
        self.vendor_bills = {b["id"]: b for b in raw.get("vendor_bills", [])}
        self.invoices = {i["id"]: i for i in raw.get("invoices", [])}
        self.payments = {p["id"]: p for p in raw.get("payments", [])}
        self.journal_entries = {j["id"]: j for j in raw.get("journal_entries", [])}
        self.fraud_flags = list(raw.get("fraud_flags") or [])
        self.last_sync = raw.get("last_sync")

    def save(self) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_sync": self.last_sync or now_iso(),
            "subsidiary": "Maya's Bakery",
            "currency": "USD",
            "vendors": list(self.vendors.values()),
            "customers": list(self.customers.values()),
            "vendor_bills": list(self.vendor_bills.values()),
            "invoices": list(self.invoices.values()),
            "payments": list(self.payments.values()),
            "journal_entries": list(self.journal_entries.values()),
            "fraud_flags": self.fraud_flags,
            "totals": self.totals(),
        }
        self.last_sync = payload["last_sync"]
        STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def totals(self) -> dict[str, int]:
        return {
            "vendors": len(self.vendors),
            "customers": len(self.customers),
            "vendor_bills": len(self.vendor_bills),
            "invoices": len(self.invoices),
            "payments": len(self.payments),
            "journal_entries": len(self.journal_entries),
            "fraud_flags": len(self.fraud_flags),
            "ap_open_cents": sum(
                b["amount_cents"] for b in self.vendor_bills.values() if b.get("status") == "Open"
            ),
            "ar_open_cents": sum(
                i["amount_cents"] for i in self.invoices.values() if i.get("status") == "Open"
            ),
        }

    def upsert_vendor(self, name: str, *, external_id: str | None = None, meta: dict | None = None) -> dict[str, Any]:
        vid = external_id or f"vend-{name.lower().replace(' ', '-')[:40]}"
        rec = self.vendors.get(vid) or {
            "id": vid,
            "entityid": name,
            "companyname": name,
            "type": "vendor",
            "balance_cents": 0,
            "created_at": now_iso(),
        }
        rec["companyname"] = name
        rec["entityid"] = name
        rec["updated_at"] = now_iso()
        if meta:
            rec["meta"] = {**(rec.get("meta") or {}), **meta}
        self.vendors[vid] = rec
        ERP.upsert_party(
            Party(id=vid, name=name, role="vendor", tier=2, amount_cents=rec["balance_cents"], meta=rec.get("meta") or {})
        )
        return rec

    def upsert_customer(self, name: str, *, external_id: str | None = None, meta: dict | None = None) -> dict[str, Any]:
        cid = external_id or f"cust-{name.lower().replace(' ', '-')[:40]}"
        rec = self.customers.get(cid) or {
            "id": cid,
            "entityid": name,
            "companyname": name,
            "type": "customer",
            "balance_cents": 0,
            "created_at": now_iso(),
        }
        rec["companyname"] = name
        rec["updated_at"] = now_iso()
        if meta:
            rec["meta"] = {**(rec.get("meta") or {}), **meta}
        self.customers[cid] = rec
        ERP.upsert_party(
            Party(id=cid, name=name, role="customer", tier=1, amount_cents=rec["balance_cents"], meta=rec.get("meta") or {})
        )
        return rec

    def post_vendor_bill(
        self,
        *,
        vendor_name: str,
        amount_cents: int,
        memo: str,
        work_item_id: str,
        status: str = "Open",
        fraud: bool = False,
    ) -> dict[str, Any]:
        vendor = self.upsert_vendor(vendor_name)
        bill_id = new_id("vbill")
        bill = {
            "id": bill_id,
            "tranid": bill_id.upper(),
            "entity": vendor["id"],
            "vendor_name": vendor_name,
            "amount_cents": amount_cents,
            "status": "Rejected" if fraud else status,
            "memo": memo,
            "work_item_id": work_item_id,
            "created_at": now_iso(),
            "recordtype": "vendorbill",
        }
        self.vendor_bills[bill_id] = bill
        vendor["balance_cents"] = int(vendor.get("balance_cents") or 0) + (0 if fraud else amount_cents)

        if fraud:
            self.fraud_flags.append(
                {
                    "id": new_id("fraud"),
                    "bill_id": bill_id,
                    "vendor": vendor_name,
                    "amount_cents": amount_cents,
                    "work_item_id": work_item_id,
                    "at": now_iso(),
                }
            )
        else:
            ERP.journals.append(
                JournalLine(
                    id=new_id("je"),
                    account_code="2000",
                    debit_cents=0,
                    credit_cents=amount_cents,
                    memo=f"AP {memo}",
                    doc_id=work_item_id,
                )
            )
            ERP.journals.append(
                JournalLine(
                    id=new_id("je"),
                    account_code="5000",
                    debit_cents=amount_cents,
                    credit_cents=0,
                    memo=f"Expense {memo}",
                    doc_id=work_item_id,
                )
            )
            ERP.upsert_account(GLAccount(code="2000", name="Accounts Payable", account_type="liability", balance_cents=vendor["balance_cents"]))
            ERP.add_flow(
                MoneyFlow(
                    id=new_id("flow"),
                    source_id="maya-bakery",
                    target_id=vendor["id"],
                    amount_cents=amount_cents,
                    kind="payable",
                    doc_id=work_item_id,
                    fraud=fraud,
                    memo=memo,
                )
            )
        return bill

    def post_customer_invoice(
        self,
        *,
        customer_name: str,
        amount_cents: int,
        memo: str,
        work_item_id: str,
        status: str = "Open",
    ) -> dict[str, Any]:
        customer = self.upsert_customer(customer_name)
        inv_id = new_id("nsinv")
        inv = {
            "id": inv_id,
            "tranid": inv_id.upper(),
            "entity": customer["id"],
            "customer_name": customer_name,
            "amount_cents": amount_cents,
            "status": status,
            "memo": memo,
            "work_item_id": work_item_id,
            "created_at": now_iso(),
            "recordtype": "invoice",
        }
        self.invoices[inv_id] = inv
        customer["balance_cents"] = int(customer.get("balance_cents") or 0) + amount_cents
        ERP.journals.append(
            JournalLine(
                id=new_id("je"),
                account_code="1200",
                debit_cents=amount_cents,
                credit_cents=0,
                memo=f"AR {memo}",
                doc_id=work_item_id,
            )
        )
        ERP.journals.append(
            JournalLine(
                id=new_id("je"),
                account_code="4000",
                debit_cents=0,
                credit_cents=amount_cents,
                memo=f"Revenue {memo}",
                doc_id=work_item_id,
            )
        )
        ERP.upsert_account(GLAccount(code="1200", name="Accounts Receivable", account_type="asset", balance_cents=customer["balance_cents"]))
        ERP.add_flow(
            MoneyFlow(
                id=new_id("flow"),
                source_id=customer["id"],
                target_id="maya-bakery",
                amount_cents=amount_cents,
                kind="receivable",
                doc_id=work_item_id,
                memo=memo,
            )
        )
        return inv

    def post_payment(
        self,
        *,
        amount_cents: int,
        memo: str,
        work_item_id: str,
        direction: str = "customer",  # customer deposit | vendor payment
        party_name: str | None = None,
    ) -> dict[str, Any]:
        pay_id = new_id("nspay")
        pay = {
            "id": pay_id,
            "tranid": pay_id.upper(),
            "amount_cents": amount_cents,
            "direction": direction,
            "party_name": party_name,
            "memo": memo,
            "work_item_id": work_item_id,
            "status": "Deposited",
            "created_at": now_iso(),
            "recordtype": "customerpayment" if direction == "customer" else "vendorpayment",
        }
        self.payments[pay_id] = pay
        # Cash JE
        if direction == "customer":
            ERP.journals.append(
                JournalLine(id=new_id("je"), account_code="1000", debit_cents=amount_cents, credit_cents=0, memo=memo, doc_id=work_item_id)
            )
            ERP.journals.append(
                JournalLine(id=new_id("je"), account_code="1200", debit_cents=0, credit_cents=amount_cents, memo=memo, doc_id=work_item_id)
            )
        else:
            ERP.journals.append(
                JournalLine(id=new_id("je"), account_code="2000", debit_cents=amount_cents, credit_cents=0, memo=memo, doc_id=work_item_id)
            )
            ERP.journals.append(
                JournalLine(id=new_id("je"), account_code="1000", debit_cents=0, credit_cents=amount_cents, memo=memo, doc_id=work_item_id)
            )
        ERP.upsert_account(GLAccount(code="1000", name="Operating Cash", account_type="asset"))
        return pay

    def post_journal(
        self,
        *,
        memo: str,
        work_item_id: str,
        lines: list[dict[str, Any]],
    ) -> dict[str, Any]:
        je_id = new_id("nsje")
        je = {
            "id": je_id,
            "tranid": je_id.upper(),
            "memo": memo,
            "work_item_id": work_item_id,
            "lines": lines,
            "created_at": now_iso(),
            "recordtype": "journalentry",
        }
        self.journal_entries[je_id] = je
        for line in lines:
            ERP.journals.append(
                JournalLine(
                    id=new_id("je"),
                    account_code=str(line.get("account") or "9999"),
                    debit_cents=int(line.get("debit_cents") or 0),
                    credit_cents=int(line.get("credit_cents") or 0),
                    memo=memo,
                    doc_id=work_item_id,
                )
            )
        return je

    def apply_gateway_post(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Map a gateway post record into NetSuite objects.
        Called from Gateway.post for destinations netsuite / ap_flag / crm / fpa / nessie / ledger.
        """
        kind = record.get("kind") or ""
        dest = record.get("destination") or "netsuite"
        amount = int(record.get("amount_cents") or 0)
        payload = record.get("payload") or {}
        wid = record.get("work_item_id") or ""
        title = record.get("subject") or wid
        created: list[dict[str, Any]] = []

        if kind == "ap_invoice" or dest == "ap_flag":
            vendor = payload.get("vendor") or "Unknown Vendor"
            fraud = bool(payload.get("blocked") or dest == "ap_flag")
            bill = self.post_vendor_bill(
                vendor_name=str(vendor),
                amount_cents=amount,
                memo=str(record.get("subject") or title),
                work_item_id=wid,
                fraud=fraud,
                status="Rejected" if fraud else "Open",
            )
            created.append({"recordtype": "vendorbill", "id": bill["id"], "fraud": fraud})

        elif kind == "ar_collect" or dest == "crm":
            customer = payload.get("customer") or "Harbor Cafe Group"
            # Collection accelerated → customer payment against AR
            inv = self.post_customer_invoice(
                customer_name=str(customer),
                amount_cents=amount,
                memo=f"AR chase {title}",
                work_item_id=wid,
                status="PaidInFull" if payload.get("collected") else "Open",
            )
            created.append({"recordtype": "invoice", "id": inv["id"]})
            if payload.get("collected"):
                pay = self.post_payment(
                    amount_cents=amount,
                    memo=f"Collection {customer}",
                    work_item_id=wid,
                    direction="customer",
                    party_name=str(customer),
                )
                created.append({"recordtype": "customerpayment", "id": pay["id"]})

        elif kind == "cash_match":
            customer = payload.get("customer") or "Harbor Cafe Group"
            gap = int(payload.get("gap_cents") or 0)
            pay = self.post_payment(
                amount_cents=amount,
                memo=f"Wire match {title}",
                work_item_id=wid,
                direction="customer",
                party_name=str(customer),
            )
            created.append({"recordtype": "customerpayment", "id": pay["id"]})
            if gap > 0 and payload.get("disposition") == "book_bank_fees":
                je = self.post_journal(
                    memo="Bank fees 6850 — short wire",
                    work_item_id=wid,
                    lines=[
                        {"account": "6850", "debit_cents": gap, "credit_cents": 0},
                        {"account": "1000", "debit_cents": 0, "credit_cents": gap},
                    ],
                )
                created.append({"recordtype": "journalentry", "id": je["id"]})
                ERP.upsert_account(GLAccount(code="6850", name="Bank Fees", account_type="expense", balance_cents=gap))

        elif kind == "spend_hold" or dest in {"nessie", "stripe_test"}:
            vendor = payload.get("vendor") or "North Bay Flour Co"
            bill = self.post_vendor_bill(
                vendor_name=str(vendor),
                amount_cents=amount,
                memo=f"Approved spend {title}",
                work_item_id=wid,
                status="PaidInFull",
            )
            pay = self.post_payment(
                amount_cents=amount,
                memo=f"Vendor payment {vendor}",
                work_item_id=wid,
                direction="vendor",
                party_name=str(vendor),
            )
            created.append({"recordtype": "vendorbill", "id": bill["id"]})
            created.append({"recordtype": "vendorpayment", "id": pay["id"]})

        elif kind == "procurement":
            vendor = payload.get("to_supplier") or payload.get("from") or "Coastal Grain Alt"
            self.upsert_vendor(str(vendor).replace("sup-", "").replace("-", " ").title(), external_id=str(vendor))
            created.append({"recordtype": "vendor", "id": str(vendor)})

        elif kind == "forecast" or dest == "fpa":
            defer = int(payload.get("defer_cents") or amount or 0)
            je = self.post_journal(
                memo="Defer non-critical spend (FPA)",
                work_item_id=wid,
                lines=[
                    {"account": "2500", "debit_cents": defer, "credit_cents": 0},
                    {"account": "6100", "debit_cents": 0, "credit_cents": defer},
                ],
            )
            created.append({"recordtype": "journalentry", "id": je["id"]})

        else:
            # Generic ledger post → memo JE
            je = self.post_journal(
                memo=f"{kind} {title}",
                work_item_id=wid,
                lines=[
                    {"account": "9999", "debit_cents": amount, "credit_cents": 0},
                    {"account": "3000", "debit_cents": 0, "credit_cents": amount},
                ],
            )
            created.append({"recordtype": "journalentry", "id": je["id"]})

        self.save()
        ERP.integrations["netsuite"] = {
            "status": "synced",
            "last_sync": self.last_sync,
            "marker": "NetSuite-shaped SoR",
            "totals": self.totals(),
        }
        ERP.save()
        log.info("netsuite applied %s → %s", wid, created)
        return {"ok": True, "created": created, "totals": self.totals(), "last_sync": self.last_sync}

    def snapshot(self) -> dict[str, Any]:
        return {
            "provider": "netsuite",
            "mode": "suite_shaped_mirror",
            "subsidiary": "Maya's Bakery",
            "status": "synced" if self.last_sync else "ready",
            "last_sync": self.last_sync,
            "totals": self.totals(),
            "vendors": list(self.vendors.values())[:40],
            "customers": list(self.customers.values())[:40],
            "vendor_bills": list(self.vendor_bills.values())[-20:],
            "invoices": list(self.invoices.values())[-20:],
            "payments": list(self.payments.values())[-20:],
            "journal_entries": list(self.journal_entries.values())[-20:],
            "fraud_flags": self.fraud_flags[-10:],
            "marker": "NetSuite-shaped SoR via gateway",
        }

    def sync_coa_from_erp(self) -> dict[str, Any]:
        """Ensure core NetSuite GL accounts exist from vault."""
        defaults = [
            ("1000", "Operating Cash", "asset"),
            ("1200", "Accounts Receivable", "asset"),
            ("2000", "Accounts Payable", "liability"),
            ("2500", "Accrued Deferred Spend", "liability"),
            ("3000", "Owner Equity", "equity"),
            ("4000", "Sales Revenue", "revenue"),
            ("5000", "COGS / Supplies", "expense"),
            ("6100", "Packaging", "expense"),
            ("6850", "Bank Fees", "expense"),
        ]
        for code, name, typ in defaults:
            if code not in ERP.accounts:
                ERP.upsert_account(GLAccount(code=code, name=name, account_type=typ))
        ERP.integrations["netsuite"]["status"] = "coa_ready"
        ERP.integrations["netsuite"]["last_sync"] = now_iso()
        ERP.save()
        self.last_sync = now_iso()
        self.save()
        return {"ok": True, "accounts": len(ERP.accounts), "last_sync": self.last_sync}


NETSUITE = NetSuiteAdapter()
