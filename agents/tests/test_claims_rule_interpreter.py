"""Tests for the fail-closed claims rule interpreter."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from claims.rule_interpreter import (
    RULE_INTERPRETATION_TOOL,
    RuleInterpretationError,
    interpret_claim_rule,
)


SOURCE_URL = "https://agency.example.gov/grants/allowable-costs"
CLEAN_TEXT = (
    "Travel costs are allowable only when they are necessary to the award. "
    "Entertainment costs are unallowable unless they have a specific programmatic purpose."
)


class FakeMessages:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.kwargs: dict[str, object] | None = None

    def create(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


class FakeClient:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.messages = FakeMessages(response=response, error=error)


def tool_response(payload: object) -> SimpleNamespace:
    return SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use",
                name="submit_claim_rule_interpretation",
                input=payload,
            )
        ]
    )


def valid_payload() -> dict[str, object]:
    return {
        "rule": "Entertainment needs a specific programmatic purpose to be allowable.",
        "exact_quote": (
            "Entertainment costs are unallowable unless they have a specific programmatic purpose."
        ),
        "source_url": SOURCE_URL,
        "confidence": 0.96,
        "needs_human": True,
        "suggested_question": "What programmatic purpose did this expense serve?",
    }


class ClaimsRuleInterpreterTests(unittest.TestCase):
    def call(self, client: FakeClient):
        return interpret_claim_rule(
            review_question="Is the staff celebration meal reimbursable?",
            clean_text=CLEAN_TEXT,
            source_url=SOURCE_URL,
            client=client,
            model="claude-test",
        )

    def assert_failure(self, payload: object, code: str) -> None:
        with self.assertRaises(RuleInterpretationError) as caught:
            self.call(FakeClient(tool_response(payload)))
        self.assertEqual(caught.exception.code, code)

    def test_accepts_one_strict_grounded_interpretation(self) -> None:
        client = FakeClient(tool_response(valid_payload()))
        result = self.call(client)

        self.assertEqual(result.rule, valid_payload()["rule"])
        self.assertTrue(result.needs_human)
        self.assertEqual(result.source_url, SOURCE_URL)

        request = client.messages.kwargs
        assert request is not None
        self.assertEqual(request["model"], "claude-test")
        self.assertEqual(request["tools"], [RULE_INTERPRETATION_TOOL])
        self.assertEqual(
            request["tool_choice"],
            {"type": "tool", "name": "submit_claim_rule_interpretation"},
        )
        self.assertIn(CLEAN_TEXT, request["messages"][0]["content"])  # type: ignore[index]

    def test_missing_required_key_fails_closed(self) -> None:
        payload = valid_payload()
        del payload["exact_quote"]
        self.assert_failure(payload, "invalid_schema")

    def test_extra_key_fails_closed(self) -> None:
        payload = valid_payload()
        payload["reasoning"] = "Unsupported hidden field"
        self.assert_failure(payload, "invalid_schema")

    def test_wrong_types_and_out_of_range_confidence_fail_closed(self) -> None:
        for field, value in (
            ("needs_human", "yes"),
            ("confidence", "0.9"),
            ("confidence", 1.01),
        ):
            with self.subTest(field=field, value=value):
                payload = valid_payload()
                payload[field] = value
                self.assert_failure(payload, "invalid_schema")

    def test_human_review_requires_a_concrete_question(self) -> None:
        payload = valid_payload()
        payload["suggested_question"] = "   "
        self.assert_failure(payload, "invalid_schema")

    def test_quote_must_exist_character_for_character(self) -> None:
        payload = valid_payload()
        payload["exact_quote"] = "Entertainment is never allowable."
        self.assert_failure(payload, "unverifiable_quote")

    def test_source_url_must_be_the_trusted_input(self) -> None:
        payload = valid_payload()
        payload["source_url"] = "https://untrusted.example/rule"
        self.assert_failure(payload, "source_mismatch")

    def test_requires_exactly_one_named_tool_call(self) -> None:
        cases = [
            SimpleNamespace(content=[]),
            SimpleNamespace(content=[SimpleNamespace(type="text", text="looks allowable")]),
            SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="tool_use",
                        name="wrong_tool",
                        input=valid_payload(),
                    )
                ]
            ),
            SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="tool_use",
                        name="submit_claim_rule_interpretation",
                        input=valid_payload(),
                    ),
                    SimpleNamespace(
                        type="tool_use",
                        name="submit_claim_rule_interpretation",
                        input=valid_payload(),
                    ),
                ]
            ),
        ]
        for response in cases:
            with self.subTest(response=response):
                with self.assertRaises(RuleInterpretationError) as caught:
                    self.call(FakeClient(response))
                self.assertEqual(caught.exception.code, "invalid_response")

    def test_api_failure_is_a_safe_stop(self) -> None:
        with self.assertRaises(RuleInterpretationError) as caught:
            self.call(FakeClient(error=TimeoutError("network timeout")))
        self.assertEqual(caught.exception.code, "claude_call_failed")

    def test_missing_credentials_is_a_safe_stop(self) -> None:
        with patch("claims.rule_interpreter._client", return_value=None):
            with self.assertRaises(RuleInterpretationError) as caught:
                interpret_claim_rule(
                    review_question="Is this reimbursable?",
                    clean_text=CLEAN_TEXT,
                    source_url=SOURCE_URL,
                )
        self.assertEqual(caught.exception.code, "claude_unavailable")

    def test_invalid_inputs_fail_before_calling_claude(self) -> None:
        client = FakeClient(tool_response(valid_payload()))
        for override in (
            {"review_question": ""},
            {"clean_text": ""},
            {"source_url": ""},
        ):
            args = {
                "review_question": "question",
                "clean_text": CLEAN_TEXT,
                "source_url": SOURCE_URL,
                "client": client,
            }
            args.update(override)
            with self.subTest(override=override):
                with self.assertRaises(RuleInterpretationError) as caught:
                    interpret_claim_rule(**args)
                self.assertEqual(caught.exception.code, "invalid_input")


if __name__ == "__main__":
    unittest.main()
