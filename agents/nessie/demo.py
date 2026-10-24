"""
Provision Maya's Bakery on Nessie and mirror demo cash events onto the bank rail.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from nessie.client import NessieClient, get_nessie, load_state, save_state

log = logging.getLogger("swarmcfo.nessie.demo")

# Berkeley bakery coords — nearby Capital One ATM/branch context
MAYA_LAT = 37.8715
MAYA_LNG = -122.2730


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def provision_maya_bakery(client: NessieClient | None = None) -> dict[str, Any]:
    """
    Ensure a Nessie customer + Checking account exist for Maya's Bakery.
    Reuses persisted IDs when still valid.
    """
    client = client or get_nessie()
    if not client.enabled:
        return {"ok": False, "error": "NESSIE_API_KEY not set", "used_nessie": False}

    state = load_state()
    customer_id = state.get("customer_id")
    account_id = state.get("account_id")

    # Validate existing account
    if customer_id and account_id:
        chk = client.get_account(account_id)
        if chk.get("ok") and isinstance(chk.get("object"), dict) and chk["object"].get("_id"):
            state["last_sync"] = _now()
            state["used_nessie"] = True
            save_state(state)
            return {
                "ok": True,
                "reused": True,
                "used_nessie": True,
                "customer_id": customer_id,
                "account_id": account_id,
                "account": chk["object"],
                "marker": "Powered by Capital One Nessie",
            }

    # Find existing Maya customer or create
    customers = client.list_customers()
    maya = next(
        (
            c
            for c in customers
            if (c.get("first_name") or "").lower() == "maya"
            and (c.get("last_name") or "").lower() in {"bakery", "chen", "owner"}
        ),
        None,
    )
    if maya:
        customer_id = maya["_id"]
        created_customer = False
    else:
        cres = client.create_customer(
            "Maya",
            "Bakery",
            street_number="2100",
            street_name="Shattuck Ave",
            city="Berkeley",
            state="CA",
            zip_code="94704",
        )
        if not cres.get("ok"):
            return {**cres, "step": "create_customer"}
        customer_id = (cres.get("object") or {}).get("_id")
        created_customer = True

    accounts = client.list_customer_accounts(customer_id)
    operating = next((a for a in accounts if "Operating" in (a.get("nickname") or "")), None)
    if operating:
        account_id = operating["_id"]
        account = operating
        created_account = False
    else:
        ares = client.create_account(
            customer_id,
            type_="Checking",
            nickname="Maya Operating",
            balance=18400,  # $18,400 opening — matches demo seed
        )
        if not ares.get("ok"):
            return {**ares, "step": "create_account", "customer_id": customer_id}
        account = ares.get("object") or {}
        account_id = account.get("_id")
        created_account = True

    atms = client.nearby_atms(MAYA_LAT, MAYA_LNG, rad=8)[:3]
    branches = client.nearby_branches(MAYA_LAT, MAYA_LNG, rad=8)[:3]

    state = {
        "customer_id": customer_id,
        "account_id": account_id,
        "account_nickname": (account or {}).get("nickname") or "Maya Operating",
        "account_number_last4": str((account or {}).get("account_number") or "")[-4:],
        "created_customer": created_customer,
        "created_account": created_account,
        "atms_nearby": [
            {"name": a.get("name"), "id": a.get("_id"), "hours": (a.get("hours") or [None])[0]}
            for a in atms
        ],
        "branches_nearby": [{"name": b.get("name"), "id": b.get("_id")} for b in branches],
        "transactions": state.get("transactions") or [],
        "last_sync": _now(),
        "used_nessie": True,
        "marker": "Powered by Capital One Nessie",
    }
    save_state(state)
    log.info("nessie provisioned customer=%s account=%s", customer_id, account_id)
    return {
        "ok": True,
        "reused": not (created_customer or created_account),
        "used_nessie": True,
        "customer_id": customer_id,
        "account_id": account_id,
        "account": account,
        "atms_nearby": state["atms_nearby"],
        "branches_nearby": state["branches_nearby"],
        "marker": state["marker"],
    }


def _record_tx(kind: str, payload: dict[str, Any], work_ref: str | None = None) -> None:
    state = load_state()
    txs = list(state.get("transactions") or [])
    txs.append(
        {
            "at": _now(),
            "kind": kind,
            "work_ref": work_ref,
            "nessie_id": (payload.get("object") or {}).get("_id"),
            "amount": (payload.get("object") or {}).get("amount"),
            "description": (payload.get("object") or {}).get("description"),
            "ok": payload.get("ok"),
        }
    )
    state["transactions"] = txs[-40:]
    state["last_sync"] = _now()
    state["used_nessie"] = True
    save_state(state)


def sync_demo_to_nessie(
    *,
    client: NessieClient | None = None,
    ar_collection_usd: float = 9200,
    supplier_deposit_usd: float = 1400,
    short_wire_usd: float = 57975,
) -> dict[str, Any]:
    """
    Mirror demo money moves onto Nessie (deposits / withdrawals).
    Called from run_demo so judges see live Capital One bank-sim traffic.
    """
    client = client or get_nessie()
    provision = provision_maya_bakery(client)
    if not provision.get("ok"):
        return provision

    account_id = provision["account_id"]
    events: list[dict[str, Any]] = []

    # Short wire in (Harbor Cafe) — deposit
    d1 = client.create_deposit(
        account_id,
        short_wire_usd,
        "NESSIE·JPM-88310442 Harbor Cafe wire (short $25)",
    )
    _record_tx("deposit", d1, "cash_match")
    events.append({"event": "short_wire_deposit", **{k: d1.get(k) for k in ("ok", "status_code", "object", "error")}})

    # Late AR acceleration — deposit
    d2 = client.create_deposit(
        account_id,
        ar_collection_usd,
        "NESSIE·AR Harbor Cafe $9,200 collection",
    )
    _record_tx("deposit", d2, "ar_collect")
    events.append({"event": "ar_collection_deposit", **{k: d2.get(k) for k in ("ok", "status_code", "object", "error")}})

    # Supplier deposit after Maya approves hold — withdrawal
    w1 = client.create_withdrawal(
        account_id,
        supplier_deposit_usd,
        "NESSIE·AP North Bay Flour Co $1,400 deposit",
    )
    _record_tx("withdrawal", w1, "spend_hold")
    events.append({"event": "supplier_withdrawal", **{k: w1.get(k) for k in ("ok", "status_code", "object", "error")}})

    acct = client.get_account(account_id)
    state = load_state()
    return {
        "ok": all(e.get("ok") for e in events),
        "used_nessie": True,
        "marker": "Powered by Capital One Nessie",
        "brand": "Capital One Nessie",
        "customer_id": provision["customer_id"],
        "account_id": account_id,
        "account": acct.get("object"),
        "events": events,
        "tx_count": len(state.get("transactions") or []),
        "atms_nearby": state.get("atms_nearby") or provision.get("atms_nearby"),
        "logo": "/nessie-mark.svg",
    }


def snapshot_for_ui() -> dict[str, Any]:
    client = get_nessie()
    status = client.status()
    state = load_state()
    return {
        **status,
        "transactions": list(reversed(state.get("transactions") or []))[:12],
        "atms_nearby": state.get("atms_nearby") or [],
        "branches_nearby": state.get("branches_nearby") or [],
        "account_number_last4": state.get("account_number_last4"),
        "logo": "/nessie-mark.svg",
        "marker": "Powered by Capital One Nessie",
    }
