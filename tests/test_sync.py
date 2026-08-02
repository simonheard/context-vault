from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from contextvault.domain import Sensitivity
from contextvault.repository import VaultRepository
from contextvault.services import ProfileService
from contextvault.sync_service import SyncService


class SyncServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repository = VaultRepository(
            Path(self.temporary_directory.name) / "vault.sqlite"
        )
        self.profile = ProfileService(self.repository)
        self.sync = SyncService(self.repository)
        self.source = self.repository.add_account("chatgpt", "Personal ChatGPT")
        self.target = self.repository.add_account("gemini", "Personal Gemini")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_preview_filters_then_run_records_diff_and_receipt(self) -> None:
        name = self.profile.add_candidate(
            attribute="identity.name", value="Simon", sensitivity=Sensitivity.PERSONAL
        )
        location = self.profile.add_candidate(
            attribute="location.current.city",
            value="New York",
            sensitivity=Sensitivity.PRIVATE,
        )
        self.profile.confirm(name.id)
        self.profile.confirm(location.id)
        route = self.sync.add_route(
            source_account_id=self.source.id,
            space="personal",
            target_account_id=self.target.id,
            policy={
                "allowed_categories": ["identity", "location"],
                "max_sensitivity": "private",
                "sensitive_mode": "ask",
            },
        )

        preview = self.sync.preview(route["id"])
        self.assertEqual([item["attribute"] for item in preview.included], ["identity.name"])
        self.assertEqual(
            [item["attribute"] for item in preview.blocked],
            ["location.current.city"],
        )

        self.sync.set_sensitive_sync(True)
        preview = self.sync.preview(route["id"])
        self.assertEqual(len(preview.awaiting_confirmation), 1)
        receipt = self.sync.run(route["id"], approve_sensitive=True)

        self.assertEqual(len(receipt["manifest"]["claims"]), 2)
        self.assertEqual(len(receipt["manifest"]["diff"]["added"]), 2)
        self.assertEqual(self.sync.list_receipts()[0]["status"], "prepared")
        self.sync.acknowledge(receipt["id"])
        self.assertEqual(self.sync.list_receipts()[0]["status"], "completed")

    def test_allow_mode_requires_matching_active_consent(self) -> None:
        claim = self.profile.add_candidate(
            attribute="location.current.city",
            value="New York",
            sensitivity=Sensitivity.PRIVATE,
        )
        self.profile.confirm(claim.id)
        route = self.sync.add_route(
            source_account_id=self.source.id,
            space="personal",
            target_account_id=self.target.id,
            policy={
                "max_sensitivity": "private",
                "sensitive_mode": "allow",
            },
        )
        self.sync.set_sensitive_sync(True)

        self.assertEqual(
            self.sync.preview(route["id"]).awaiting_confirmation[0]["reason"],
            "consent_required",
        )
        wrong = self.sync.record_consent(route["id"], ["health"], "allow")
        self.assertTrue(self.sync.preview(route["id"]).awaiting_confirmation)
        self.sync.revoke_consent(wrong)
        self.sync.record_consent(route["id"], ["location"], "allow")

        self.assertEqual(len(self.sync.preview(route["id"]).included), 1)

    def test_full_automation_requires_warning_and_only_runs_changed_routes(self) -> None:
        claim = self.profile.add_candidate(attribute="identity.name", value="Simon")
        self.profile.confirm(claim.id)
        route = self.sync.add_route(
            source_account_id=self.source.id,
            space="personal",
            target_account_id=self.target.id,
        )
        with self.assertRaisesRegex(ValueError, "risk acknowledgement"):
            self.sync.configure_automation(route["id"], enabled=True)

        self.sync.configure_automation(
            route["id"], enabled=True, interval_minutes=5, risk_acknowledged=True
        )
        self.assertEqual(len(self.sync.automation_jobs()), 1)
        prepared = self.sync.run_automation(route["id"])
        self.assertEqual(self.sync.automation_jobs(), [])
        failed = self.sync.fail_receipt(prepared["id"], "composer changed")
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(len(self.sync.automation_jobs()), 1)
        retry = self.sync.run_automation(route["id"])
        self.sync.acknowledge(retry["id"])
        self.assertEqual(self.sync.automation_jobs(), [])


if __name__ == "__main__":
    unittest.main()
