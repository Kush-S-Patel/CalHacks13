"""Restart and append-only guarantees for the guided claims SQLite store."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from claims.guided_persistence import GuidedPersistence
from sow.models import (
    AI_CLAIMS,
    FINANCE_MANAGER,
    SYNC,
    Policy,
    Precedent,
)
from sow.store import SystemOfWork


class GuidedPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.store = GuidedPersistence(Path(self.temp_dir.name) / "guided.sqlite3")

    @staticmethod
    def _build_claim_world(claim_id: str) -> tuple[SystemOfWork, SimpleNamespace]:
        sow = SystemOfWork(room_id="persistence-test")
        prepare = sow.create_work(
            SYNC,
            kind="claim_prepare",
            subject=claim_id,
            title="Prepare reimbursement claim",
            amount_cents=281_350,
            evidence=[claim_id, "source-ledger"],
        )
        sow.propose(
            prepare.id,
            AI_CLAIMS,
            patch={"payload": {"revision": 2}},
            reason="Prepared corrected package for manager review.",
        )
        question = sow.create_work(
            SYNC,
            kind="claim_question",
            subject=claim_id,
            title="Resolve staff-lunch treatment",
            evidence=[claim_id],
        )
        sow.ask(question.id, AI_CLAIMS, "Is this staff lunch award-related?")

        policy = Policy(
            id="pol-staff-lunch",
            version=1,
            title="Hold staff-only lunches",
            rule="Hold staff-only lunch charges for finance-manager review.",
            condition={"description_contains": ["staff lunch"]},
            action={"hold_for_human_review": True},
            evidence=[claim_id, question.id],
        )
        sow.propose_policy(AI_CLAIMS, policy)
        sow.approve_policy(policy.id, FINANCE_MANAGER)

        precedent = Precedent(
            id="prec-staff-lunch",
            kind="claim_exception_resolution",
            summary="Staff-only lunch was excluded after human review.",
            subject=claim_id,
            correction={"decision": "exclude", "ledger_id": "GL-9005"},
            tags=["staff-lunch", "human-reviewed"],
            created_by=FINANCE_MANAGER.id,
        )
        sow.add_precedent(precedent)

        package = SimpleNamespace(
            id=claim_id,
            work_item_ids=[prepare.id],
            meta={
                "guided_flow": {
                    "prepare_work_item_id": prepare.id,
                    "question_work_item_id": question.id,
                    "policy_id": policy.id,
                    "precedent_id": precedent.id,
                }
            },
        )
        return sow, package

    def test_artifacts_and_audit_survive_a_fresh_system_of_work(self) -> None:
        source, package = self._build_claim_world("claim-restart-001")
        expected_audit = source.audit.for_subject(package.id)

        self.store.save_claim(source, package)
        fresh = SystemOfWork(room_id="fresh-process")
        counts = self.store.restore_claim(fresh, package.id)

        self.assertEqual(counts["work_items"], 2)
        self.assertEqual(counts["policies"], 1)
        self.assertEqual(counts["precedents"], 1)
        self.assertEqual(counts["audit_events"], len(expected_audit))
        self.assertEqual(
            fresh.work_items[package.work_item_ids[0]].to_dict(),
            source.work_items[package.work_item_ids[0]].to_dict(),
        )
        question_id = package.meta["guided_flow"]["question_work_item_id"]
        self.assertEqual(fresh.work_items[question_id].state, "NEEDS_INFO")
        self.assertEqual(fresh.work_items[question_id].question, "Is this staff lunch award-related?")
        self.assertEqual(fresh.policies["pol-staff-lunch"].status, "active")
        self.assertEqual(fresh.policies["pol-staff-lunch"].approved_by, FINANCE_MANAGER.id)
        self.assertEqual(
            fresh.precedents["prec-staff-lunch"].correction,
            {"decision": "exclude", "ledger_id": "GL-9005"},
        )
        self.assertEqual(fresh.audit.all(), expected_audit)

        # Restoring again merges by event ID rather than duplicating receipts.
        self.store.restore_claim(fresh, package.id)
        self.assertEqual(fresh.audit.all(), expected_audit)

    def test_repeated_saves_keep_one_immutable_row_per_audit_event(self) -> None:
        source, package = self._build_claim_world("claim-idempotent-001")
        expected_audit = source.audit.for_subject(package.id)

        self.store.save_claim(source, package)
        self.store.save_claim(source, package)
        self.store.save_claim(source, package)

        rows = self.store.audit_rows(package.id)
        self.assertEqual(len(rows), len(expected_audit))
        self.assertEqual({row["id"] for row in rows}, {row["id"] for row in expected_audit})
        self.assertEqual(rows, expected_audit)

    def test_one_receipt_can_be_restored_for_each_claim_it_evidences(self) -> None:
        source = SystemOfWork(room_id="cross-claim-audit")
        event = source.audit.append(
            actor=FINANCE_MANAGER.id,
            action="link_claims",
            subject="cross-period-review",
            allowed=True,
            reason="The October hold follows the approved September precedent.",
            diff={"linked": {"from": None, "to": True}},
            evidence=["claim-september", "claim-october"],
        )
        september = SimpleNamespace(id="claim-september", work_item_ids=[], meta={})
        october = SimpleNamespace(id="claim-october", work_item_ids=[], meta={})

        self.store.save_claim(source, september)
        self.store.save_claim(source, october)

        september_world = SystemOfWork()
        october_world = SystemOfWork()
        self.store.restore_claim(september_world, september.id)
        self.store.restore_claim(october_world, october.id)
        self.assertEqual(september_world.audit.all(), [event.to_dict()])
        self.assertEqual(october_world.audit.all(), [event.to_dict()])


if __name__ == "__main__":
    unittest.main()
