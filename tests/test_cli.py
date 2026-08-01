from __future__ import annotations

import contextlib
import io
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
            self.assertEqual(status(vault_path).schema_version, 4)
            self.assertIn("Claims: 0", output.getvalue())
            self.assertIn("Devices: 0", output.getvalue())
            self.assertIn("Provider accounts: 0", output.getvalue())
            self.assertIn("Profile spaces: 0", output.getvalue())
            self.assertIn("Sync routes: 0", output.getvalue())
            self.assertIn("Sync targets: 0", output.getvalue())

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


if __name__ == "__main__":
    unittest.main()
