"""Proof that an approved rule changes a genuinely separate later claim."""

from __future__ import annotations

import unittest

from claims.guided_flow import (
    approve_policy,
    attempt_ai_approval,
    propose_policy,
    resolve_exception,
    submit_decision,
    submit_next_period_claim,
)
from claims.learning_loop import start_claims_learning
from claims.session import clear_all_pending
from claims.store import CLAIMS
from sow.store import SystemOfWork


class FutureClaimSubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_all_pending()
        self.sow = SystemOfWork(room_id="test-future-claim")

    def _start(self):
        started = start_claims_learning(self.sow)
        package = CLAIMS.get(started["claim_id"])
        assert package is not None
        return package

    def _activate_policy(self):
        package = self._start()
        submit_decision(
            self.sow,
            claim_id=package.id,
            decision="exclude",
            reason="Staff-only lunch; exclude it from the federal award.",
        )
        resolve_exception(
            self.sow,
            claim_id=package.id,
            ledger_id="GL-9007",
            action="exclude",
            reason="Confirmed duplicate of GL-9006.",
        )
        resolve_exception(
            self.sow,
            claim_id=package.id,
            ledger_id="GL-9008",
            action="exclude",
            reason="October payroll belongs to the next reporting period.",
        )
        resolve_exception(
            self.sow,
            claim_id=package.id,
            ledger_id="GL-9009",
            action="attach_receipt",
            reason="Finance manager verified the toner receipt.",
            evidence_id=f"ev-toner-{package.id}",
            filename="staples_toner_0922.pdf",
        )
        proposal = propose_policy(
            self.sow,
            claim_id=package.id,
            reason="Create a narrow reusable rule from this correction.",
        )
        policy_id = proposal["policy"]["id"]
        approve_policy(
            self.sow,
            policy_id=policy_id,
            reason="Approve this rule with a mandatory human hold.",
        )
        return package, policy_id

    def test_submission_is_blocked_until_policy_is_active(self) -> None:
        package = self._start()
        with self.assertRaisesRegex(RuntimeError, "cannot be submitted during phase"):
            submit_next_period_claim(
                self.sow,
                source_claim_id=package.id,
                reason="Try a later claim too early.",
            )

    def test_independent_clean_claim_is_held_only_by_exact_approved_policy(self) -> None:
        source, policy_id = self._activate_policy()
        source_status = source.status
        source_totals = dict(source.totals)

        result = submit_next_period_claim(
            self.sow,
            source_claim_id=source.id,
            reason="Test the approved learned rule on a separate October submission.",
        )
        future = result["future_claim"]
        work = result["future_claim_work_item"]

        self.assertFalse(result["idempotent"])
        self.assertEqual(result["phase"], "future_claim_held")
        self.assertNotEqual(future["id"], source.id)
        self.assertEqual(future["reporting_period"], "2025-10")
        self.assertEqual(result["baseline"]["status"], "ready_for_approval")
        self.assertEqual(result["baseline"]["exception_codes"], [])
        self.assertEqual(result["baseline"]["claimed_cents"], 86_000)
        self.assertEqual(future["matches"][0]["exception_codes"], ["learned_policy_hold"])
        self.assertEqual(future["exceptions"][0]["code"], "learned_policy_hold")
        self.assertEqual(future["exceptions"][0]["policy_id"], policy_id)
        self.assertEqual(future["exceptions"][0]["source_claim_id"], source.id)
        self.assertEqual(future["totals"]["held_cents"], 86_000)
        self.assertEqual(future["totals"]["recon_gap_cents"], 0)
        self.assertEqual(work["kind"], "claim_policy_hold")
        self.assertEqual(work["state"], "HELD")
        self.assertEqual(work["policy_id"], policy_id)
        self.assertEqual(work["subject"], future["id"])
        self.assertEqual(work["payload"]["baseline_exception_codes"], [])
        self.assertEqual(result["match_basis"]["policy_id"], policy_id)
        self.assertIn("staff lunch", result["match_basis"]["matched_terms"])
        self.assertTrue(
            future["meta"]["learned_policy_application"]["audit_event_id"].startswith("aud-")
        )

        # The source package is linked, not mutated into the October package.
        self.assertEqual(source.status, source_status)
        self.assertEqual(source.totals, source_totals)
        self.assertEqual(
            source.meta["guided_flow"]["future_claim_id"],
            future["id"],
        )
        audit_actions = {
            event["action"] for event in self.sow.audit.for_subject(future["id"])
        }
        self.assertIn("apply_learned_claim_policy", audit_actions)
        self.assertIn("hold", audit_actions)

    def test_repeat_is_idempotent_and_ai_approval_requires_future_hold(self) -> None:
        source, _ = self._activate_policy()
        with self.assertRaisesRegex(RuntimeError, "during phase policy_active"):
            attempt_ai_approval(
                self.sow,
                claim_id=source.id,
                reason="Do not skip the independent later-claim proof.",
            )

        first = submit_next_period_claim(
            self.sow,
            source_claim_id=source.id,
            reason="Test the approved learned rule.",
        )
        work_count = len(self.sow.work_items)
        claim_count = len(CLAIMS.packages)
        second = submit_next_period_claim(
            self.sow,
            source_claim_id=source.id,
            reason="Repeat the same stage action.",
        )
        self.assertTrue(second["idempotent"])
        self.assertEqual(second["future_claim"]["id"], first["future_claim"]["id"])
        self.assertEqual(
            second["future_claim_work_item"]["id"],
            first["future_claim_work_item"]["id"],
        )
        self.assertEqual(len(self.sow.work_items), work_count)
        self.assertEqual(len(CLAIMS.packages), claim_count)

        denied = attempt_ai_approval(
            self.sow,
            claim_id=source.id,
            reason="Now test the code-enforced approval boundary.",
        )
        self.assertTrue(denied["denied"])
        self.assertEqual(denied["phase"], "ai_approval_denied")

    def test_nonmatching_submission_does_not_create_a_hold(self) -> None:
        source, _ = self._activate_policy()
        before_work = len(self.sow.work_items)
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            submit_next_period_claim(
                self.sow,
                source_claim_id=source.id,
                reason="This should remain outside the narrow learned policy.",
                vendor="Office Depot",
                description="Training packet paper",
            )
        self.assertEqual(len(self.sow.work_items), before_work)
        self.assertEqual(source.meta["guided_flow"]["phase"], "policy_active")
        self.assertNotIn("future_claim_id", source.meta["guided_flow"])


if __name__ == "__main__":
    unittest.main()
