"""Fail-closed adapter for the Apify grant-rule source Actor.

The custom Actor is expected to accept one source URL and emit one dataset item
with this contract::

    {
        "source_url": "https://official.example/rule",
        "title": "Current reimbursement rule",
        "clean_text": "...",
        "fetched_at": "2026-10-24T20:15:00Z",
        "content_hash": "<sha256 of clean_text>",
        "changed": true,
        "previous_hash": null
    }

This module deliberately has no stale-data fallback. Missing configuration,
failed Actor runs, empty datasets, and malformed or inconsistent source data all
raise :class:`ApifySourceError` so the Claims workflow can create a human-review
hold instead of making a decision from unverified text.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from config import settings

APIFY_API_BASE_URL = "https://api.apify.com/v2"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ApifySourceError(RuntimeError):
    """Base error that callers must convert into a review hold."""


class ApifyConfigError(ApifySourceError):
    """Required Apify configuration is missing."""


class ApifyRequestError(ApifySourceError):
    """The Apify API could not return a successful, parseable response."""


class ApifyValidationError(ApifySourceError):
    """The Actor output does not satisfy the trusted-source contract."""


def sha256_text(text: str) -> str:
    """Return the Actor contract's content hash for exact UTF-8 text."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ApifyRuleSource:
    """Validated rule text plus the Apify receipt needed for audit evidence."""

    source_url: str
    title: str
    clean_text: str
    fetched_at: str
    content_hash: str
    changed: bool
    previous_hash: str | None
    actor_id: str
    run_id: str
    dataset_id: str

    @property
    def url(self) -> str:
        """Alias used by consumers that call the source field ``url``."""

        return self.source_url

    @property
    def change_metadata(self) -> dict[str, Any]:
        return {
            "changed": self.changed,
            "previous_hash": self.previous_hash,
            "current_hash": self.content_hash,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["change"] = self.change_metadata
        return payload


class ApifyRuleSourceClient:
    """Run one configured Actor and validate its single-source dataset."""

    def __init__(
        self,
        *,
        token: str | None = None,
        actor_id: str | None = None,
        api_base_url: str = APIFY_API_BASE_URL,
        timeout_seconds: float = 75.0,
        wait_for_finish_seconds: int = 60,
    ) -> None:
        self._token = (token if token is not None else os.getenv("APIFY_TOKEN", "")).strip()
        self.actor_id = (
            actor_id if actor_id is not None else os.getenv("APIFY_ACTOR_ID", "")
        ).strip()
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.wait_for_finish_seconds = wait_for_finish_seconds

        missing = []
        if not self._token:
            missing.append("APIFY_TOKEN")
        if not self.actor_id:
            missing.append("APIFY_ACTOR_ID")
        if missing:
            raise ApifyConfigError(f"Missing required configuration: {', '.join(missing)}")
        if timeout_seconds <= 0:
            raise ApifyConfigError("timeout_seconds must be positive")
        if not 0 <= wait_for_finish_seconds <= 60:
            raise ApifyConfigError("wait_for_finish_seconds must be between 0 and 60")

    def fetch(
        self,
        source_url: str,
        *,
        previous_hash: str | None = None,
    ) -> ApifyRuleSource:
        """Run the Actor, read its dataset, and return only validated output."""

        source_url = _validate_public_url(source_url, field="source_url")
        previous_hash = _validate_optional_hash(previous_hash, field="previous_hash")

        run_data = self._start_run(source_url, previous_hash)
        run_id = _required_string(run_data, "id", context="Actor run")
        status = _required_string(run_data, "status", context="Actor run").upper()
        if status != "SUCCEEDED":
            raise ApifyRequestError(f"Actor run {run_id} finished with status {status}")

        dataset_id = _required_string(run_data, "defaultDatasetId", context="Actor run")
        items = self._read_dataset(dataset_id)
        if not items:
            raise ApifyValidationError(f"Dataset {dataset_id} contained no rule-source item")
        if len(items) != 1:
            raise ApifyValidationError(
                f"Dataset {dataset_id} must contain exactly one item; received {len(items)}"
            )

        return _validate_item(
            items[0],
            requested_url=source_url,
            expected_previous_hash=previous_hash,
            actor_id=self.actor_id,
            run_id=run_id,
            dataset_id=dataset_id,
        )

    def _start_run(self, source_url: str, previous_hash: str | None) -> dict[str, Any]:
        actor_path = quote(self.actor_id, safe="~")
        query = urlencode({"waitForFinish": self.wait_for_finish_seconds})
        body: dict[str, Any] = {"urls": [source_url]}
        if previous_hash is not None:
            body["previous_hash"] = previous_hash
        response = self._request_json(
            "POST",
            f"/actors/{actor_path}/runs?{query}",
            body=body,
        )
        data = response.get("data") if isinstance(response, dict) else None
        if not isinstance(data, dict):
            raise ApifyRequestError("Actor run response did not contain a data object")
        return data

    def _read_dataset(self, dataset_id: str) -> list[dict[str, Any]]:
        dataset_path = quote(dataset_id, safe="")
        query = urlencode({"clean": "true", "format": "json", "limit": 2})
        response = self._request_json(
            "GET",
            f"/datasets/{dataset_path}/items?{query}",
        )
        if not isinstance(response, list):
            raise ApifyRequestError("Dataset response was not a JSON array")
        if any(not isinstance(item, dict) for item in response):
            raise ApifyValidationError("Dataset contained a non-object item")
        return response

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> Any:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            f"{self.api_base_url}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "User-Agent": "SwarmCFO-Claims/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                status = getattr(response, "status", 200)
        except HTTPError as exc:
            raise ApifyRequestError(f"Apify request failed with HTTP {exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ApifyRequestError(f"Apify request failed: {exc}") from exc

        if not 200 <= status < 300:
            raise ApifyRequestError(f"Apify request failed with HTTP {status}")
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ApifyRequestError("Apify response exceeded the maximum allowed size")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApifyRequestError("Apify returned an invalid JSON response") from exc


def fetch_rule_source(
    source_url: str,
    *,
    previous_hash: str | None = None,
    token: str | None = None,
    actor_id: str | None = None,
) -> ApifyRuleSource:
    """Convenience entry point for the Claims rules-refresh handler."""

    return ApifyRuleSourceClient(
        token=token if token is not None else os.getenv("APIFY_TOKEN", settings.apify_token),
        actor_id=actor_id if actor_id is not None else os.getenv("APIFY_ACTOR_ID", settings.apify_actor_id),
    ).fetch(
        source_url,
        previous_hash=previous_hash,
    )


def _validate_item(
    item: dict[str, Any],
    *,
    requested_url: str,
    expected_previous_hash: str | None,
    actor_id: str,
    run_id: str,
    dataset_id: str,
) -> ApifyRuleSource:
    item_url_value = item.get("source_url")
    if item_url_value is None:
        item_url_value = item.get("url")
    if not isinstance(item_url_value, str):
        raise ApifyValidationError("Actor output source_url must be a string")
    item_url = _validate_public_url(item_url_value, field="source_url")
    if item_url != requested_url:
        raise ApifyValidationError("Actor output source_url did not match the requested URL")

    title = _required_string(item, "title", context="Actor output")
    clean_text_value = item.get("clean_text")
    if not isinstance(clean_text_value, str) or not clean_text_value.strip():
        raise ApifyValidationError("Actor output clean_text must be a non-empty string")
    # Preserve the Actor's exact text bytes: content_hash authenticates this value,
    # and downstream citation checks must search the same text.
    clean_text = clean_text_value
    fetched_at = _required_string(item, "fetched_at", context="Actor output")
    _validate_timestamp(fetched_at)

    content_hash = _validate_hash(item.get("content_hash"), field="content_hash")
    computed_hash = sha256_text(clean_text)
    if content_hash != computed_hash:
        raise ApifyValidationError("Actor output content_hash did not match clean_text")

    changed = item.get("changed")
    if not isinstance(changed, bool):
        raise ApifyValidationError("Actor output changed must be a boolean")

    item_previous_hash = _validate_optional_hash(
        item.get("previous_hash"),
        field="previous_hash",
    )
    if item_previous_hash != expected_previous_hash:
        raise ApifyValidationError("Actor output previous_hash did not match the run input")
    expected_changed = expected_previous_hash is None or expected_previous_hash != content_hash
    if changed != expected_changed:
        raise ApifyValidationError("Actor output changed was inconsistent with the content hashes")

    return ApifyRuleSource(
        source_url=item_url,
        title=title,
        clean_text=clean_text,
        fetched_at=fetched_at,
        content_hash=content_hash,
        changed=changed,
        previous_hash=item_previous_hash,
        actor_id=actor_id,
        run_id=run_id,
        dataset_id=dataset_id,
    )


def _required_string(mapping: dict[str, Any], key: str, *, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ApifyValidationError(f"{context} {key} must be a non-empty string")
    return value.strip()


def _validate_hash(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ApifyValidationError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def _validate_optional_hash(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    return _validate_hash(value, field=field)


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApifyValidationError("fetched_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ApifyValidationError("fetched_at must include a timezone")


def _validate_public_url(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApifyValidationError(f"{field} must be a non-empty URL")
    value = value.strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ApifyValidationError(f"{field} must use http or https and include a host")
    if parsed.username is not None or parsed.password is not None:
        raise ApifyValidationError(f"{field} must not contain credentials")
    hostname = parsed.hostname.lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ApifyValidationError(f"{field} must be a public URL")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ApifyValidationError(f"{field} must be a public URL")
    return value
