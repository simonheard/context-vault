from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from contextvault.gui import (
    create_profile_space,
    create_provider_account,
    dashboard_snapshot,
    list_rows,
)
from contextvault.vault import initialize


class GuiDataTests(unittest.TestCase):
    def test_dashboard_and_account_management(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault_path = Path(directory) / "vault.sqlite"
            initialize(vault_path)

            account = create_provider_account(vault_path, "Gemini", "Personal Gemini")
            create_profile_space(vault_path, "work", "Work")
            snapshot = dashboard_snapshot(vault_path)

            self.assertEqual(account["platform"], "gemini")
            self.assertEqual(snapshot["counts"]["accounts"], 1)
            self.assertEqual(snapshot["counts"]["spaces"], 2)
            self.assertEqual(len(list_rows(vault_path, "provider_accounts")), 1)

    def test_rejects_unsupported_provider(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault_path = Path(directory) / "vault.sqlite"
            initialize(vault_path)

            with self.assertRaisesRegex(ValueError, "Unsupported provider"):
                create_provider_account(vault_path, "unknown", "Unknown")


if __name__ == "__main__":
    unittest.main()
