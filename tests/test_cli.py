from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from contextvault.cli import main
from contextvault.vault import status


class CliTests(unittest.TestCase):
    def test_init_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault_path = Path(directory) / "vault.sqlite"

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                init_code = main(["--vault", str(vault_path), "init"])
                status_code = main(["--vault", str(vault_path), "status"])

            self.assertEqual(init_code, 0)
            self.assertEqual(status_code, 0)
            self.assertEqual(status(vault_path).schema_version, 9)
            self.assertIn("Claims: 0", output.getvalue())
            self.assertIn("Devices: 0", output.getvalue())
            self.assertIn("Provider accounts: 0", output.getvalue())
            self.assertIn("Profile spaces: 1", output.getvalue())
            self.assertIn("Sync routes: 0", output.getvalue())
            self.assertIn("Sync targets: 0", output.getvalue())
            self.assertIn("Attachment references: 0", output.getvalue())
            self.assertIn("Sync events: 0", output.getvalue())

            with sqlite3.connect(vault_path) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
            self.assertTrue(
                {
                    "entities",
                    "schema_migrations",
                    "claims",
                    "claim_sources",
                    "devices",
                    "provider_accounts",
                    "profile_spaces",
                    "claim_spaces",
                    "sync_targets",
                    "sync_routes",
                    "sync_receipts",
                    "consent_receipts",
                    "attachment_refs",
                    "sync_events",
                    "device_sync_cursors",
                    "source_imports",
                    "evidence_messages",
                    "generated_summaries",
                    "cli_installations",
                    "sync_clients",
                    "capture_sources",
                    "claims_fts",
                }.issubset(tables)
            )

    def test_status_reports_missing_vault(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault_path = Path(directory) / "missing.sqlite"
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                code = main(["--vault", str(vault_path), "status"])

            self.assertEqual(code, 2)
            self.assertIn("Vault does not exist", errors.getvalue())

    def test_profile_workflow_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault_path = Path(directory) / "vault.sqlite"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "--vault",
                            str(vault_path),
                            "claims",
                            "add",
                            "identity.location",
                            "New York",
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(["--vault", str(vault_path), "claims", "list"]), 0
                )
                self.assertEqual(
                    main(["--vault", str(vault_path), "events", "list"]), 0
                )

            value = output.getvalue()
            self.assertIn("Added candidate:", value)
            self.assertIn('"attribute": "identity.location"', value)
            self.assertIn('"event_type": "claim.created"', value)

    def test_cli_exports_a_standalone_extension_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault_path = root / "vault.sqlite"
            output_path = root / "browser.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--vault", str(vault_path), "claims", "add", "preference.editor", "Vim"]), 0)
                self.assertEqual(main(["--vault", str(vault_path), "claims", "confirm-all"]), 0)
                self.assertEqual(main(["--vault", str(vault_path), "profile", "export-browser", str(output_path)]), 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], 1)
            self.assertEqual(payload["claims"][0]["status"], "confirmed")
            self.assertEqual(payload["claims"][0]["value"], "Vim")


if __name__ == "__main__":
    unittest.main()
