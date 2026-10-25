"""Focused regression tests for the explicit guided claim workflow."""

from __future__ import annotations

import unittest

from claims.guided_flow import (
    approve_claim,
    approve_policy,
    attempt_ai_approval,
    guided_state,
    propose_policy,
    resolve_exception,
    submit_decision,
    submit_next_period_claim,
)
from claims.learning_loop import start_claims_learning
from claims.session import clear_all_pending
from claims.store import CLAIMS
from sow.models import FINANCE_MANAGER
from sow.store import SystemOfWork


class GuidedClaimsTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_all_pending()
        self.sow = SystemOfWork(room_id="test-guided-claims")

    def _start(self):
        started = start_claims_learning(self.sow)
        package = CLAIMS.get(started["claim_id"])
        assert package is not None
        return started, package

    def test_decision_requires_reason_and_only_changes_catering(self) -> None:
        started, package = self._start()
        untouched_ids = {"GL-9007", "GL-9008", "GL-9009"}
        before_codes = {
            match.ledger_id: list(match.exception_codes)
            for match in package.matches
            if match.ledger_id in untouched_ids
        }
        before_exceptions = [
            dict(ex)
            for ex in package.exceptions
            if isinstance(ex, dict) and ex.get("ledger_id") in untouched_ids
        ]

        with self.assertRaisesRegex(ValueError, "reason is required"):
            submit_decision(
                self.sow,
                claim_id=package.id,
                decision="exclude",
                reason="   ",
            )
        self.assertEqual(self.sow.work_items[started["ask_work_item_id"]].state, "NEEDS_INFO")

        result = submit_decision(
            self.sow,
            claim_id=package.id,
            decision="exclude",
            reason="Staff-only celebration; no direct programmatic purpose.",
        )
        updated = CLAIMS.get(package.id)
        assert updated is not None
        catering = next(m for m in updated.matches if m.ledger_id == "GL-9005")
        after_codes = {
            match.ledger_id: list(match.exception_codes)
            for match in updated.matches
            if match.ledger_id in untouched_ids
        }
        after_exceptions = [
            dict(ex)
            for ex in updated.exceptions
            if isinstance(ex, dict) and ex.get("ledger_id") in untouched_ids
        ]

        self.assertTrue(result["ok"])
        self.assertEqual(catering.exception_codes, ["excluded_from_claim"])
        self.assertEqual(before_codes, after_codes)
        self.assertEqual(before_exceptions, after_exceptions)
        self.assertEqual(updated.status, "exceptions")
        self.assertEqual(updated.totals["claimed_cents"], 3_023_500)
        self.assertEqual(updated.totals["excluded_cents"], 86_000)
        self.assertTrue(result["unresolved_exceptions"])

    def test_guided_read_recovers_handles_from_open_work_items(self) -> None:
        started, package = self._start()
        package.meta.pop("loop_session", None)
        state = guided_state(self.sow, started["claim_id"])
        self.assertEqual(state["phase"], "awaiting_decision")
        self.assertEqual(state["claim_id"], package.id)

    def test_full_guided_flow_keeps_actions_separate(self) -> None:
        started, package = self._start()
        submit_decision(
            self.sow,
            claim_id=package.id,
            decision="exclude",
            reason="Staff-only celebration; exclude from the award.",
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
        resolved = resolve_exception(
            self.sow,
            claim_id=package.id,
            ledger_id="GL-9009",
            action="attach_receipt",
            reason="Finance manager verified the vendor receipt.",
            evidence_id="ev-guided-toner",
            filename="staples_toner_0922.pdf",
        )
        self.assertEqual(resolved["unresolved_exceptions"], [])
        self.assertEqual(resolved["claim"]["status"], "ready_for_approval")
        self.assertEqual(resolved["claim"]["totals"]["eligible_cents"], 2_813_500)
        self.assertEqual(resolved["claim"]["totals"]["excluded_cents"], 816_000)

        proposed = propose_policy(
            self.sow,
            claim_id=package.id,
            reason="Turn this correction into a reusable review rule.",
        )
        policy_id = proposed["policy"]["id"]
        self.assertEqual(proposed["policy"]["status"], "needs_approval")
        activated = approve_policy(
            self.sow,
            policy_id=policy_id,
            reason="The rule is narrow, evidence-backed, and keeps a human hold.",
        )
        self.assertEqual(activated["policy"]["status"], "active")

        future = submit_next_period_claim(
            self.sow,
            source_claim_id=package.id,
            reason="Verify the approved policy on an independent October claim.",
        )
        self.assertEqual(future["phase"], "future_claim_held")
        self.assertNotEqual(future["future_claim"]["id"], package.id)
        self.assertEqual(future["future_claim_work_item"]["state"], "HELD")

        with self.assertRaisesRegex(RuntimeError, "prove the AI approval boundary"):
            approve_claim(
                self.sow,
                claim_id=package.id,
                reason="Approve the corrected package.",
            )

        denied = attempt_ai_approval(
            self.sow,
            claim_id=package.id,
            reason="Agent requests approval of its prepared package.",
        )
        self.assertTrue(denied["denied"])
        self.assertIn("cannot approve", denied["denial_receipt"]["authorization_reason"])
        self.assertEqual(denied["claim"]["status"], "ready_for_approval")

        approved = approve_claim(
            self.sow,
            claim_id=package.id,
            reason="All line exceptions are resolved and evidence is attached.",
        )
        prepare = self.sow.work_items[started["prepare_work_item_id"]]
        self.assertEqual(approved["phase"], "approved")
        self.assertEqual(approved["claim"]["status"], "approved")
        self.assertEqual(prepare.state, "APPROVED")
        self.assertEqual(prepare.approved_by, FINANCE_MANAGER.id)
        self.assertEqual(prepare.amount_cents, 2_813_500)
        self.assertEqual(prepare.payload["revision"], 2)
        self.assertEqual(prepare.payload["eligible_cents"], 2_813_500)
        self.assertEqual(prepare.payload["excluded_cents"], 816_000)
        self.assertEqual(prepare.payload["critical_exceptions"], [])
        self.assertEqual(approved["claim"]["meta"]["unauthorized_approvals"], 0)
        self.assertIn("_Status: approved", approved["claim"]["schedules_md"])

    def test_keep_decision_can_reach_a_human_review_policy(self) -> None:
        _, package = self._start()
        submit_decision(
            self.sow,
            claim_id=package.id,
            decision="keep",
            reason="Program mentors attended; retain only with documented purpose and support.",
        )
        with self.assertRaisesRegex(RuntimeError, "resolve every claim exception"):
            propose_policy(
                self.sow,
                claim_id=package.id,
                reason="Do not skip the remaining line reviews.",
            )
        resolve_exception(
            self.sow,
            claim_id=package.id,
            ledger_id="GL-9005",
            action="attach_receipt",
            reason="Linked catering support and the manager's program-purpose record.",
            evidence_id="ev-guided-catering",
            filename="catering_program_lunch.pdf",
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
            reason="Linked the toner receipt record.",
            evidence_id="ev-guided-toner-keep",
            filename="staples_toner_0922.pdf",
        )
        proposed = propose_policy(
            self.sow,
            claim_id=package.id,
            reason="Require support and human review for future staff-event charges.",
        )
        self.assertEqual(proposed["policy"]["status"], "needs_approval")
        self.assertTrue(proposed["policy"]["action"]["require_supporting_evidence"])
        self.assertFalse(proposed["policy"]["action"]["exclude_from_claim"])

    def test_manager_approval_is_blocked_while_other_exceptions_remain(self) -> None:
        _, package = self._start()
        submit_decision(
            self.sow,
            claim_id=package.id,
            decision="exclude",
            reason="Staff-only celebration.",
        )
        with self.assertRaisesRegex(RuntimeError, "unresolved exceptions"):
            approve_claim(
                self.sow,
                claim_id=package.id,
                reason="Approve anyway.",
            )


if __name__ == "__main__":
    unittest.main()
