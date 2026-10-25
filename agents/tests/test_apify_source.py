"""Tests for the fail-closed Apify rule-source adapter."""

from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from claims.apify_source import (
    ApifyConfigError,
    ApifyRequestError,
    ApifyRuleSourceClient,
    ApifyValidationError,
    sha256_text,
)


class _FakeResponse:
    def __init__(self, payload: object, status: int = 200) -> None:
        self._raw = json.dumps(payload).encode("utf-8")
        self.status = status

    def read(self, _size: int = -1) -> bytes:
        return self._raw

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class ApifyRuleSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_url = "https://example.org/grants/current-rule"
        self.text = "Travel requires written pre-approval from the program manager."
        self.current_hash = sha256_text(self.text)

    def _item(self, **overrides: object) -> dict[str, object]:
        item: dict[str, object] = {
            "source_url": self.source_url,
            "title": "Current reimbursement rule",
            "clean_text": self.text,
            "fetched_at": "2026-10-24T20:15:00Z",
            "content_hash": self.current_hash,
            "changed": True,
            "previous_hash": None,
        }
        item.update(overrides)
        return item

    def test_missing_configuration_fails_before_network(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch(
            "claims.apify_source.urlopen"
        ) as mocked_urlopen:
            with self.assertRaisesRegex(
                ApifyConfigError,
                "APIFY_TOKEN, APIFY_ACTOR_ID",
            ):
                ApifyRuleSourceClient()
            mocked_urlopen.assert_not_called()

    def test_success_uses_actor_and_returns_provenance(self) -> None:
        run_response = {
            "data": {
                "id": "run-123",
                "status": "SUCCEEDED",
                "defaultDatasetId": "dataset-456",
            }
        }
        calls = [_FakeResponse(run_response), _FakeResponse([self._item()])]

        with patch("claims.apify_source.urlopen", side_effect=calls) as mocked_urlopen:
            result = ApifyRuleSourceClient(
                token="secret-token",
                actor_id="swarmcfo~grant-rule-watcher",
            ).fetch(self.source_url)

        self.assertEqual(result.run_id, "run-123")
        self.assertEqual(result.dataset_id, "dataset-456")
        self.assertEqual(result.actor_id, "swarmcfo~grant-rule-watcher")
        self.assertEqual(result.url, self.source_url)
        self.assertEqual(result.clean_text, self.text)
        self.assertEqual(
            result.change_metadata,
            {
                "changed": True,
                "previous_hash": None,
                "current_hash": self.current_hash,
            },
        )

        start_request = mocked_urlopen.call_args_list[0].args[0]
        self.assertEqual(start_request.get_method(), "POST")
        self.assertIn(
            "/actors/swarmcfo~grant-rule-watcher/runs?waitForFinish=60",
            start_request.full_url,
        )
        self.assertNotIn("secret-token", start_request.full_url)
        self.assertEqual(start_request.get_header("Authorization"), "Bearer secret-token")
        self.assertEqual(
            json.loads(start_request.data.decode("utf-8")),
            {"urls": [self.source_url]},
        )

        dataset_request = mocked_urlopen.call_args_list[1].args[0]
        self.assertEqual(dataset_request.get_method(), "GET")
        self.assertIn("/datasets/dataset-456/items?", dataset_request.full_url)

    def test_unchanged_result_requires_matching_previous_hash(self) -> None:
        run_response = {
            "data": {
                "id": "run-same",
                "status": "SUCCEEDED",
                "defaultDatasetId": "dataset-same",
            }
        }
        item = self._item(changed=False, previous_hash=self.current_hash)
        calls = [_FakeResponse(run_response), _FakeResponse([item])]

        with patch("claims.apify_source.urlopen", side_effect=calls):
            result = ApifyRuleSourceClient(token="token", actor_id="actor").fetch(
                self.source_url,
                previous_hash=self.current_hash,
            )

        self.assertFalse(result.changed)
        self.assertEqual(result.previous_hash, self.current_hash)

    def test_clean_text_is_preserved_for_hash_and_citation_checks(self) -> None:
        exact_text = "  Exact rule text with deliberate spacing.\n"
        run_response = {
            "data": {
                "id": "run-exact",
                "status": "SUCCEEDED",
                "defaultDatasetId": "dataset-exact",
            }
        }
        item = self._item(
            clean_text=exact_text,
            content_hash=sha256_text(exact_text),
        )
        calls = [_FakeResponse(run_response), _FakeResponse([item])]

        with patch("claims.apify_source.urlopen", side_effect=calls):
            result = ApifyRuleSourceClient(token="token", actor_id="actor").fetch(
                self.source_url
            )

        self.assertEqual(result.clean_text, exact_text)

    def test_failed_actor_run_fails_closed_without_dataset_read(self) -> None:
        run_response = {
            "data": {
                "id": "run-failed",
                "status": "FAILED",
                "defaultDatasetId": "dataset-unused",
            }
        }
        with patch(
            "claims.apify_source.urlopen",
            return_value=_FakeResponse(run_response),
        ) as mocked_urlopen:
            with self.assertRaisesRegex(ApifyRequestError, "status FAILED"):
                ApifyRuleSourceClient(token="token", actor_id="actor").fetch(
                    self.source_url
                )
        self.assertEqual(mocked_urlopen.call_count, 1)

    def test_empty_dataset_fails_closed(self) -> None:
        run_response = {
            "data": {
                "id": "run-empty",
                "status": "SUCCEEDED",
                "defaultDatasetId": "dataset-empty",
            }
        }
        calls = [_FakeResponse(run_response), _FakeResponse([])]
        with patch("claims.apify_source.urlopen", side_effect=calls):
            with self.assertRaisesRegex(ApifyValidationError, "contained no"):
                ApifyRuleSourceClient(token="token", actor_id="actor").fetch(
                    self.source_url
                )

    def test_hash_mismatch_fails_closed(self) -> None:
        run_response = {
            "data": {
                "id": "run-bad-hash",
                "status": "SUCCEEDED",
                "defaultDatasetId": "dataset-bad-hash",
            }
        }
        bad_item = self._item(content_hash="0" * 64)
        calls = [_FakeResponse(run_response), _FakeResponse([bad_item])]
        with patch("claims.apify_source.urlopen", side_effect=calls):
            with self.assertRaisesRegex(ApifyValidationError, "did not match clean_text"):
                ApifyRuleSourceClient(token="token", actor_id="actor").fetch(
                    self.source_url
                )

    def test_change_metadata_must_be_consistent(self) -> None:
        previous_hash = "1" * 64
        run_response = {
            "data": {
                "id": "run-bad-change",
                "status": "SUCCEEDED",
                "defaultDatasetId": "dataset-bad-change",
            }
        }
        bad_item = self._item(changed=False, previous_hash=previous_hash)
        calls = [_FakeResponse(run_response), _FakeResponse([bad_item])]
        with patch("claims.apify_source.urlopen", side_effect=calls):
            with self.assertRaisesRegex(ApifyValidationError, "changed was inconsistent"):
                ApifyRuleSourceClient(token="token", actor_id="actor").fetch(
                    self.source_url,
                    previous_hash=previous_hash,
                )


if __name__ == "__main__":
    unittest.main()
