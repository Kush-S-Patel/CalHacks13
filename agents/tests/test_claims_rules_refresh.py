"""Rules refresh endpoint logic — live Apify + Claude receipts without network."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from claims.apify_source import ApifyRuleSource, ApifySourceError
from claims.guided_persistence import GuidedPersistence
from claims.learning_loop import start_claims_learning
from claims.rule_interpreter import RuleInterpretation, RuleInterpretationError
from claims.rules_refresh import claim_audit_chain, refresh_claim_rule
from claims.store import ClaimStore
from sow.store import SystemOfWork


def _sample_source() -> ApifyRuleSource:
    text = (
        "Costs of entertainment, including amusement, diversion, and social activities "
        "and any associated costs (such as gifts), are unallowable unless they have a "
        "specific and direct programmatic purpose and are included in a Federal award."
    )
    return ApifyRuleSource(
        source_url="https://www.govinfo.gov/example/rule",
        title="2 CFR § 200.438",
        clean_text=text,
        fetched_at="2026-10-24T20:15:00Z",
        content_hash="abc",
        changed=True,
        previous_hash=None,
        actor_id="actor-demo",
        run_id="run-demo-001",
        dataset_id="dataset-demo-001",
    )


def _sample_interpretation(source: ApifyRuleSource) -> RuleInterpretation:
    quote = (
        "Costs of entertainment, including amusement, diversion, and social activities "
        "and any associated costs (such as gifts), are unallowable unless they have a "
        "specific and direct programmatic purpose and are included in a Federal award."
    )
    return RuleInterpretation(
        rule="Entertainment costs need a direct programmatic purpose in the award.",
        exact_quote=quote,
        source_url=source.source_url,
        confidence=0.92,
        needs_human=True,
        suggested_question="Was the catering tied to a direct programmatic purpose?",
    )


class RulesRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.claims = ClaimStore(root / "claims")
        self.persistence = GuidedPersistence(root / "guided.sqlite3")
        self.sow = SystemOfWork(room_id="rules-refresh")

    def _start_claim(self) -> str:
        with patch("claims.learning_loop.CLAIMS", self.claims), patch(
            "claims.pipeline.CLAIMS", self.claims
        ), patch("claims.session.CLAIMS", self.claims), patch(
            "claims.learning_loop.GUIDED_PERSISTENCE", self.persistence
        ):
            started = start_claims_learning(self.sow)
        return started["claim_id"]

    def test_success_stores_live_receipts_and_updates_rule_source(self) -> None:
        claim_id = self._start_claim()
        source = _sample_source()
        interpretation = _sample_interpretation(source)

        with patch("claims.rules_refresh.CLAIMS", self.claims), patch(
            "claims.rules_refresh.GUIDED_PERSISTENCE", self.persistence
        ), patch("claims.rules_refresh.fetch_rule_source", return_value=source), patch(
            "claims.rules_refresh.interpret_claim_rule", return_value=interpretation
        ):
            result = refresh_claim_rule(self.sow, claim_id)

        self.assertEqual(result["status"], "needs_human")
        claim = result["claim"]
        self.assertFalse(claim["meta"]["rule_source"]["live_refresh"])
        receipts = claim["meta"]["provider_receipts"]
        self.assertEqual(receipts["apify"]["run_id"], "run-demo-001")
        self.assertEqual(receipts["claude"]["confidence"], 0.92)

    def test_high_confidence_without_human_review_applies_rule_source(self) -> None:
        claim_id = self._start_claim()
        source = _sample_source()
        interpretation = _sample_interpretation(source).model_copy(
            update={"needs_human": False, "confidence": 0.95}
        )

        with patch("claims.rules_refresh.CLAIMS", self.claims), patch(
            "claims.rules_refresh.GUIDED_PERSISTENCE", self.persistence
        ), patch("claims.rules_refresh.fetch_rule_source", return_value=source), patch(
            "claims.rules_refresh.interpret_claim_rule", return_value=interpretation
        ):
            result = refresh_claim_rule(self.sow, claim_id)

        self.assertEqual(result["status"], "applied")
        self.assertTrue(result["claim"]["meta"]["rule_source"]["live_refresh"])
        self.assertEqual(result["claim"]["meta"]["rule_source"]["apify_run_id"], "run-demo-001")
        reloaded = ClaimStore(self.claims.root).get(claim_id)
        self.assertTrue(reloaded.meta["rule_source"]["live_refresh"])
        self.assertEqual(reloaded.meta["provider_receipts"]["apify"]["run_id"], "run-demo-001")

    def test_apify_failure_is_fail_closed(self) -> None:
        claim_id = self._start_claim()
        with patch("claims.rules_refresh.CLAIMS", self.claims), patch(
            "claims.rules_refresh.GUIDED_PERSISTENCE", self.persistence
        ), patch(
            "claims.rules_refresh.fetch_rule_source",
            side_effect=ApifySourceError("Actor run failed"),
        ):
            with self.assertRaises(ValueError):
                refresh_claim_rule(self.sow, claim_id)
        reloaded = ClaimStore(self.claims.root).get(claim_id)
        self.assertEqual(reloaded.meta["rule_refresh"]["status"], "source_failed")
        self.assertFalse(reloaded.meta["rule_source"]["live_refresh"])

    def test_rule_cannot_change_after_manager_decision(self) -> None:
        claim_id = self._start_claim()
        package = self.claims.get(claim_id)
        package.meta["guided_flow"] = {"decision": {"decision": "exclude"}}
        with patch("claims.rules_refresh.CLAIMS", self.claims), patch(
            "claims.rules_refresh.fetch_rule_source"
        ) as provider:
            with self.assertRaisesRegex(ValueError, "before recording"):
                refresh_claim_rule(self.sow, claim_id)
            provider.assert_not_called()

    def test_interpretation_failure_is_fail_closed(self) -> None:
        claim_id = self._start_claim()
        source = _sample_source()
        with patch("claims.rules_refresh.CLAIMS", self.claims), patch(
            "claims.rules_refresh.GUIDED_PERSISTENCE", self.persistence
        ), patch("claims.rules_refresh.fetch_rule_source", return_value=source), patch(
            "claims.rules_refresh.interpret_claim_rule",
            side_effect=RuleInterpretationError("unverifiable_quote", "quote missing"),
        ):
            with self.assertRaises(ValueError):
                refresh_claim_rule(self.sow, claim_id)

    def test_audit_chain_returns_persisted_refresh_event(self) -> None:
        claim_id = self._start_claim()
        source = _sample_source()
        interpretation = _sample_interpretation(source).model_copy(
            update={"needs_human": False, "confidence": 0.95}
        )
        with patch("claims.rules_refresh.CLAIMS", self.claims), patch(
            "claims.rules_refresh.GUIDED_PERSISTENCE", self.persistence
        ), patch("claims.rules_refresh.fetch_rule_source", return_value=source), patch(
            "claims.rules_refresh.interpret_claim_rule", return_value=interpretation
        ):
            refresh_claim_rule(self.sow, claim_id)

        with patch("claims.rules_refresh.CLAIMS", self.claims):
            chain = claim_audit_chain(self.sow, claim_id)
        self.assertGreaterEqual(chain["count"], 1)
        self.assertIn(
            "refresh_rule_source",
            {event["action"] for event in chain["events"]},
        )


if __name__ == "__main__":
    unittest.main()
