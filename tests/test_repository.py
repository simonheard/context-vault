from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from contextvault.domain import ClaimStatus, Sensitivity
from contextvault.repository import VaultRepository
from contextvault.services import ProfileService
from contextvault.device_agent import _version


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.vault_path = Path(self.temporary_directory.name) / "vault.sqlite"
        self.repository = VaultRepository(self.vault_path)
        self.service = ProfileService(self.repository)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_candidate_confirmation_builds_profile_and_events(self) -> None:
        candidate = self.service.add_candidate(
            attribute="work.role",
            value="Software engineer",
            confidence=0.9,
        )

        self.assertEqual(candidate.status, ClaimStatus.CANDIDATE)
        self.assertEqual(len(self.service.candidates()), 1)

        confirmed = self.service.confirm(candidate.id)
        profile = self.service.current_profile()

        self.assertEqual(confirmed.status, ClaimStatus.CONFIRMED)
        self.assertEqual(profile["claim_count"], 1)
        self.assertEqual(profile["categories"]["work"][0]["value"], "Software engineer")
        self.assertEqual(
            [event.event_type for event in self.repository.list_events()],
            ["entity.created", "claim.created", "claim.confirmed"],
        )

    def test_secret_claims_are_never_stored(self) -> None:
        with self.assertRaisesRegex(ValueError, "Secret-class"):
            self.service.add_candidate(
                attribute="credentials.password",
                value="never-store-this",
                sensitivity=Sensitivity.SECRET,
            )

        self.assertEqual(self.repository.list_claims(), [])

    def test_attachment_is_a_provider_reference(self) -> None:
        account = self.repository.add_account("gemini", "Personal Gemini")
        attachment = self.repository.add_attachment_ref(
            account_id=account.id,
            provider_file_id="provider-file-123",
            filename="device-inventory.txt",
            remote_url="https://example.invalid/provider-file-123",
            mime_type="text/plain",
        )

        stored = self.repository.list_attachment_refs(account.id)

        self.assertEqual(stored, [attachment])
        self.assertEqual(stored[0].provider_file_id, "provider-file-123")
        self.assertEqual(stored[0].extracted_text, None)
        self.assertIn(
            "attachment.created",
            [event.event_type for event in self.repository.list_events()],
        )

    def test_device_cursor_is_monotonic_state(self) -> None:
        self.assertEqual(self.repository.get_cursor("laptop"), 0)
        self.repository.set_cursor("laptop", 12)
        self.assertEqual(self.repository.get_cursor("laptop"), 12)

    def test_device_scan_upserts_and_reports_changes(self) -> None:
        scan = {
            "display_name": "Test laptop",
            "device_type": "computer",
            "fingerprint": "stable-fingerprint",
            "config": {"os": "TestOS", "tools": {"python": "3.12"}},
        }
        created = self.repository.upsert_device_scan(scan)
        scan["config"]["tools"]["python"] = "3.13"
        updated = self.repository.upsert_device_scan(scan)

        self.assertEqual(created["id"], updated["id"])
        self.assertIn("tools", updated["changes"])
        self.assertEqual(len(self.repository.list_devices()), 1)

    def test_full_text_search_and_account_lifecycle(self) -> None:
        account = self.repository.add_account("chatgpt", "Personal")
        claim = self.service.add_candidate(attribute="project.name", value="ContextVault")

        self.assertEqual(self.repository.search_claims("ContextVault"), [claim])
        renamed = self.repository.update_account(account.id, label="Work", status="disconnected")
        self.assertEqual(renamed.account_label, "Work")
        self.assertEqual(renamed.status, "disconnected")

    def test_extension_pairing_token_can_be_revoked(self) -> None:
        original = self.repository.extension_pairing_token()
        rotated = self.repository.rotate_extension_pairing_token()
        self.assertNotEqual(original, rotated)
        self.assertEqual(self.repository.extension_pairing_token(), rotated)

    def test_client_protocol_registration_tracks_compatibility(self) -> None:
        active = self.repository.register_client("extension-1", "extension", "0.2", 2)
        future = self.repository.register_client("future", "extension", "9.0", 99)
        self.assertEqual(active["status"], "active")
        self.assertTrue(self.repository.authorize_local_token(active["client_token"]))
        self.assertEqual(future["status"], "incompatible")
        self.assertFalse(self.repository.authorize_local_token(future["client_token"]))
        self.assertEqual(len(self.repository.list_clients()), 2)
        self.assertNotIn("token_hash", self.repository.list_clients()[0])

    def test_accepts_registered_domestic_provider(self) -> None:
        account = self.repository.add_account("deepseek", "Personal DeepSeek")
        self.assertEqual(account.platform, "deepseek")

    @patch("contextvault.device_agent.subprocess.run")
    @patch("contextvault.device_agent.shutil.which", return_value="/usr/bin/tool")
    def test_failed_tool_probe_is_not_reported(self, _which, run) -> None:
        run.return_value.returncode = 1
        run.return_value.stdout = ""
        run.return_value.stderr = "tool is unavailable"
        self.assertIsNone(_version(["tool", "--version"]))


if __name__ == "__main__":
    unittest.main()
