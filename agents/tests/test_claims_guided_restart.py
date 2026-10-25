"""End-to-end restart proof for the governed Claims workflow."""

from __future__ import annotations

import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

from claims.guided_flow import (
    approve_claim,
    approve_policy,
    attempt_ai_approval,
    propose_policy,
    resolve_exception,
    submit_decision,
    submit_next_period_claim,
)
from claims.guided_persistence import GuidedPersistence
from claims.learning_loop import start_claims_learning
from claims.session import clear_all_pending
from claims.store import ClaimStore
from sow.models import FINANCE_MANAGER
from sow.store import SystemOfWork


class GuidedClaimsRestartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.claim_root = root / "claims"
        self.persistence = GuidedPersistence(root / "guided.sqlite3")

    @contextmanager
    def _environment(self, claims: ClaimStore):
        """Point every imported Claims module at one isolated durable store."""
        with ExitStack() as stack:
            for target in (
                "claims.guided_flow.CLAIMS",
                "claims.learning_loop.CLAIMS",
                "claims.pipeline.CLAIMS",
                "claims.session.CLAIMS",
            ):
                stack.enter_context(patch(target, claims))
            stack.enter_context(
                patch("claims.guided_flow.GUIDED_PERSISTENCE", self.persistence)
            )
            stack.enter_context(
                patch("claims.learning_loop.GUIDED_PERSISTENCE", self.persistence)
            )
            yield

    @staticmethod
    def _reach_future_hold(sow: SystemOfWork, claim_id: str) -> tuple[str, str]:
        submit_decision(
            sow,
            claim_id=claim_id,
            decision="exclude",
            reason="Staff-only celebration; no direct program purpose.",
        )
        resolve_exception(
            sow,
            claim_id=claim_id,
            ledger_id="GL-9007",
            action="exclude",
            reason="Confirmed duplicate of GL-9006.",
        )
        resolve_exception(
            sow,
            claim_id=claim_id,
            ledger_id="GL-9008",
            action="exclude",
            reason="October payroll belongs to the next reporting month.",
        )
        resolve_exception(
            sow,
            claim_id=claim_id,
            ledger_id="GL-9009",
            action="attach_receipt",
            reason="Finance manager verified the toner receipt record.",
            evidence_id=f"ev-restart-{claim_id}",
            filename="staples_toner_0922.pdf",
        )
        proposed = propose_policy(
            sow,
            claim_id=claim_id,
            reason="Create a reusable rule from the manager correction.",
        )
        policy_id = proposed["policy"]["id"]
        approve_policy(
            sow,
            policy_id=policy_id,
            reason="Narrow rule; preserve a mandatory human hold.",
        )
        future = submit_next_period_claim(
            sow,
            source_claim_id=claim_id,
            reason="Test the approved rule on an independent October claim.",
        )
        return policy_id, future["future_claim"]["id"]

    def test_restart_restores_artifacts_and_workflow_continues(self) -> None:
        initial_claims = ClaimStore(self.claim_root)
        first_world = SystemOfWork(room_id="before-restart")
        with self._environment(initial_claims):
            clear_all_pending()
            started = start_claims_learning(first_world)
            claim_id = started["claim_id"]
            prepare_id = started["prepare_work_item_id"]
            policy_id, future_claim_id = self._reach_future_hold(first_world, claim_id)
            audit_ids_before = {
                row["id"] for row in self.persistence.audit_rows(claim_id)
            }

        # New objects simulate a backend process restart. Claim JSON and the
        # governed System-of-Work artifacts are loaded from separate stores.
        restarted_claims = ClaimStore(self.claim_root)
        restarted_world = SystemOfWork(room_id="after-restart")
        counts = self.persistence.restore_claim(restarted_world, claim_id)
        with self._environment(restarted_claims):
            source = restarted_claims.get(claim_id)
            future = restarted_claims.get(future_claim_id)
            self.assertIsNotNone(source)
            self.assertIsNotNone(future)
            self.assertGreaterEqual(counts["work_items"], 3)
            self.assertEqual(restarted_world.policies[policy_id].status, "active")
            self.assertEqual(
                source.meta["guided_flow"]["phase"],  # type: ignore[union-attr]
                "future_claim_held",
            )

            denied = attempt_ai_approval(
                restarted_world,
                claim_id=claim_id,
                reason="Prove the automated actor cannot approve its own package.",
            )
            self.assertTrue(denied["denied"])
            approved = approve_claim(
                restarted_world,
                claim_id=claim_id,
                reason="All exceptions are resolved and the role boundary is proven.",
            )
            self.assertEqual(approved["phase"], "approved")

        # A second restart proves the terminal state and append-only receipts
        # were persisted, rather than merely remaining in process memory.
        final_claims = ClaimStore(self.claim_root)
        final_world = SystemOfWork(room_id="second-restart")
        self.persistence.restore_claim(final_world, claim_id)
        final_source = final_claims.get(claim_id)
        self.assertIsNotNone(final_source)
        self.assertEqual(final_source.status, "approved")  # type: ignore[union-attr]
        self.assertEqual(
            final_source.meta["guided_flow"]["phase"],  # type: ignore[union-attr]
            "approved",
        )
        self.assertEqual(final_world.work_items[prepare_id].state, "APPROVED")
        self.assertEqual(final_world.work_items[prepare_id].approved_by, FINANCE_MANAGER.id)
        self.assertEqual(final_world.policies[policy_id].status, "active")
        persisted_rows = self.persistence.audit_rows(claim_id)
        persisted_ids = [row["id"] for row in persisted_rows]
        self.assertEqual(len(persisted_ids), len(set(persisted_ids)))
        self.assertTrue(audit_ids_before.issubset(set(persisted_ids)))
        self.assertIn(
            "claim_manager_approval",
            {row["action"] for row in persisted_rows},
        )


if __name__ == "__main__":
    unittest.main()
