from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from contextvault.capture_service import CaptureService
from contextvault.domain import ClaimStatus
from contextvault.repository import VaultRepository


class CaptureServiceTests(unittest.TestCase):
    def test_capture_requires_consent_and_imports_candidates_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = VaultRepository(Path(directory) / "vault.sqlite")
            account = repository.add_account("chatgpt", "Personal ChatGPT")
            service = CaptureService(repository)
            with self.assertRaisesRegex(ValueError, "risk acknowledgement"):
                service.configure(account.id, enabled=True)
            service.configure(
                account.id,
                enabled=True,
                interval_minutes=5,
                risk_acknowledged=True,
                conversation_url="https://chatgpt.com/c/example",
            )
            self.assertEqual(len(service.jobs()), 1)
            payload = {
                "provider": "chatgpt",
                "conversation_url": "https://chatgpt.com/c/example",
                "title": "About me",
                "messages": [
                    {"id": "m1", "role": "user", "content": "My name is Simon. I live in New York."},
                    {"id": "m2", "role": "assistant", "content": "Thanks."},
                ],
            }
            first = service.ingest(account.id, **payload)
            second = service.ingest(account.id, **payload)
            self.assertEqual(first["candidates"], 2)
            self.assertEqual(second["candidates"], 0)
            self.assertEqual(len(repository.list_claims(status=ClaimStatus.CANDIDATE)), 2)
            self.assertEqual(service.jobs(), [])

    def test_capture_rejects_provider_account_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = VaultRepository(Path(directory) / "vault.sqlite")
            account = repository.add_account("gemini", "Gemini")
            with self.assertRaisesRegex(ValueError, "does not match"):
                CaptureService(repository).ingest(
                    account.id,
                    provider="chatgpt",
                    conversation_url="https://chatgpt.com/c/example",
                    title="Wrong account",
                    messages=[{"role": "user", "content": "My name is Simon"}],
                )

    def test_capture_pauses_after_three_adapter_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = VaultRepository(Path(directory) / "vault.sqlite")
            account = repository.add_account("deepseek", "DeepSeek")
            service = CaptureService(repository)
            service.configure(account.id, enabled=True, risk_acknowledged=True)
            for _ in range(3):
                state = service.record_failure(account.id, "page selectors changed")
            self.assertEqual(state["paused_reason"], "three_consecutive_adapter_failures")
            self.assertEqual(service.jobs(), [])

    def test_knowledge_probe_extracts_assistant_output_as_low_confidence_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = VaultRepository(Path(directory) / "vault.sqlite")
            account = repository.add_account("chatgpt", "ChatGPT")
            result = CaptureService(repository).ingest(
                account.id,
                provider="chatgpt",
                conversation_url="https://chatgpt.com/c/profile-probe",
                title="Profile probe",
                messages=[
                    {"role": "user", "content": "Summarize what you know about me"},
                    {"role": "assistant", "content": "My name is Simon. I work at Example Corp."},
                ],
                knowledge_probe=True,
            )
            self.assertEqual(result["candidates"], 2)
            claims = repository.list_claims(status=ClaimStatus.CANDIDATE)
            self.assertTrue(all(item.confidence < 0.7 for item in claims))


if __name__ == "__main__":
    unittest.main()
