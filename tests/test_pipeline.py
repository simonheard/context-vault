from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from contextvault.domain import ClaimStatus
from contextvault.pipeline import ImportPipeline
from contextvault.repository import VaultRepository


class ImportPipelineTests(unittest.TestCase):
    def test_chatgpt_json_import_extracts_candidates_and_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = root / "conversations.json"
            export.write_text(
                json.dumps(
                    [
                        {
                            "id": "conversation-1",
                            "title": "About me",
                            "mapping": {
                                "node-1": {
                                    "message": {
                                        "id": "message-1",
                                        "author": {"role": "user"},
                                        "content": {
                                            "parts": [
                                                "My name is Simon. I live in New York. I work at Example Corp."
                                            ]
                                        },
                                        "create_time": 1,
                                    }
                                }
                            },
                        }
                    ]
                ),
                encoding="utf-8",
            )
            repository = VaultRepository(root / "vault.sqlite")
            pipeline = ImportPipeline(repository)

            first = pipeline.import_chatgpt(export)
            second = pipeline.import_chatgpt(export)

            self.assertEqual(first.conversations, 1)
            self.assertEqual(first.messages, 1)
            self.assertEqual(first.candidates, 3)
            self.assertEqual(second.candidates, 0)
            self.assertEqual(second.duplicates, 3)
            self.assertEqual(
                len(repository.list_claims(status=ClaimStatus.CANDIDATE)), 3
            )
            self.assertEqual(len(repository.list_imports()), 1)

    def test_secret_message_is_redacted_and_not_extracted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = root / "conversations.json"
            export.write_text(
                json.dumps(
                    [
                        {
                            "id": "secret-chat",
                            "messages": [
                                {
                                    "id": "secret-message",
                                    "role": "user",
                                    "content": "My name is Simon and password=hunter12345",
                                }
                            ],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            repository = VaultRepository(root / "vault.sqlite")

            result = ImportPipeline(repository).import_chatgpt(export)

            self.assertEqual(result.candidates, 0)
            self.assertEqual(repository.list_claims(), [])
            evidence = repository.list_evidence_messages(result.import_id)
            self.assertTrue(evidence[0]["content"].startswith("[REDACTED:"))
            self.assertNotIn("hunter12345", evidence[0]["content"])


if __name__ == "__main__":
    unittest.main()
