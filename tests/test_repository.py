from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from contextvault.domain import ClaimStatus, Sensitivity
from contextvault.repository import VaultRepository
from contextvault.services import ProfileService


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


if __name__ == "__main__":
    unittest.main()
