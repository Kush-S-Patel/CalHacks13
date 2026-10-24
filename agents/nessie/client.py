"""
HTTP client for Capital One Nessie Hackathon API.
https://api.nessieisreal.com — key as ?key= query param (HTTPS).
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from config import settings

log = logging.getLogger("swarmcfo.nessie")

BASE_URL = "https://api.nessieisreal.com"
STATE_PATH = Path(__file__).resolve().parents[2] / "data" / "nessie_state.json"


class NessieClient:
    def __init__(self, api_key: str | None = None, *, base_url: str = BASE_URL) -> None:
        self.api_key = (api_key or settings.nessie_api_key or "").strip()
        self.base_url = base_url.rstrip("/")
        self.enabled = bool(self.api_key)
        self._http = httpx.Client(timeout=30.0, follow_redirects=True)

    def close(self) -> None:
        self._http.close()

    def _params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        p: dict[str, Any] = {"key": self.api_key}
        if extra:
            p.update(extra)
        return p

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "error": "NESSIE_API_KEY not set", "used_nessie": False}
        url = f"{self.base_url}{path}"
        try:
            r = self._http.request(
                method,
                url,
                params=self._params(params),
                json=json_body,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
        except httpx.HTTPError as e:
            log.warning("nessie %s %s failed: %s", method, path, e)
            return {"ok": False, "error": str(e), "used_nessie": True, "path": path}

        text = r.text
        try:
            data: Any = r.json() if text else {}
        except json.JSONDecodeError:
            data = {"raw": text}

        ok = 200 <= r.status_code < 300
        out: dict[str, Any] = {
            "ok": ok,
            "status_code": r.status_code,
            "used_nessie": True,
            "path": path,
            "data": data,
        }
        if isinstance(data, dict) and "objectCreated" in data:
            out["object"] = data["objectCreated"]
        elif isinstance(data, dict) and "objectUpdated" in data:
            out["object"] = data["objectUpdated"]
        elif ok:
            out["object"] = data
        if not ok:
            out["error"] = data if not isinstance(data, dict) else data.get("message") or data
        return out

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        return self.request("GET", path, params=params or None)

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", path, json_body=body)

    def put(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self.request("PUT", path, json_body=body)

    # ── domain helpers ───────────────────────────────────────────────────

    def list_customers(self) -> list[dict[str, Any]]:
        res = self.get("/customers")
        data = res.get("data")
        return data if isinstance(data, list) else []

    def create_customer(
        self,
        first_name: str,
        last_name: str,
        *,
        street_number: str,
        street_name: str,
        city: str,
        state: str,
        zip_code: str,
    ) -> dict[str, Any]:
        return self.post(
            "/customers",
            {
                "first_name": first_name,
                "last_name": last_name,
                "address": {
                    "street_number": street_number,
                    "street_name": street_name,
                    "city": city,
                    "state": state,
                    "zip": zip_code,
                },
            },
        )

    def create_account(
        self,
        customer_id: str,
        *,
        type_: str = "Checking",
        nickname: str,
        balance: float | int,
        rewards: int = 0,
    ) -> dict[str, Any]:
        return self.post(
            f"/customers/{customer_id}/accounts",
            {
                "type": type_,
                "nickname": nickname,
                "rewards": rewards,
                "balance": balance,
            },
        )

    def get_account(self, account_id: str) -> dict[str, Any]:
        return self.get(f"/accounts/{account_id}")

    def list_customer_accounts(self, customer_id: str) -> list[dict[str, Any]]:
        res = self.get(f"/customers/{customer_id}/accounts")
        data = res.get("data")
        return data if isinstance(data, list) else []

    def create_deposit(
        self,
        account_id: str,
        amount: float | int,
        description: str,
        *,
        medium: str = "balance",
        status: str = "completed",
        transaction_date: str | None = None,
    ) -> dict[str, Any]:
        return self.post(
            f"/accounts/{account_id}/deposits",
            {
                "medium": medium,
                "transaction_date": transaction_date or date.today().isoformat(),
                "status": status,
                "amount": amount,
                "description": description[:120],
            },
        )

    def create_withdrawal(
        self,
        account_id: str,
        amount: float | int,
        description: str,
        *,
        medium: str = "balance",
        status: str = "completed",
        transaction_date: str | None = None,
    ) -> dict[str, Any]:
        return self.post(
            f"/accounts/{account_id}/withdrawals",
            {
                "medium": medium,
                "transaction_date": transaction_date or date.today().isoformat(),
                "status": status,
                "amount": amount,
                "description": description[:120],
            },
        )

    def nearby_atms(self, lat: float, lng: float, rad: float = 5.0) -> list[dict[str, Any]]:
        res = self.get("/atms", lat=lat, lng=lng, rad=rad)
        data = res.get("data")
        return data if isinstance(data, list) else []

    def nearby_branches(self, lat: float, lng: float, rad: float = 5.0) -> list[dict[str, Any]]:
        res = self.get("/branches", lat=lat, lng=lng, rad=rad)
        data = res.get("data")
        return data if isinstance(data, list) else []

    def status(self) -> dict[str, Any]:
        state = load_state()
        if not self.enabled:
            return {
                "provider": "nessie",
                "brand": "Capital One Nessie",
                "status": "missing_key",
                "used_nessie": False,
                "docs": "https://api.nessieisreal.com/",
            }
        ping = self.get("/customers")
        return {
            "provider": "nessie",
            "brand": "Capital One Nessie",
            "status": "connected" if ping.get("ok") else "error",
            "used_nessie": True,
            "api": self.base_url,
            "docs": "https://api.nessieisreal.com/",
            "customer_id": state.get("customer_id"),
            "account_id": state.get("account_id"),
            "account_nickname": state.get("account_nickname"),
            "last_sync": state.get("last_sync"),
            "tx_count": len(state.get("transactions") or []),
            "error": ping.get("error") if not ping.get("ok") else None,
        }


_client: NessieClient | None = None


def get_nessie() -> NessieClient:
    global _client
    if _client is None:
        _client = NessieClient()
    return _client


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
