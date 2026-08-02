from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from contextvault.cli_adapters import CliAdapterService
from contextvault.repository import VaultRepository
from contextvault.services import ProfileService


class CliAdapterTests(unittest.TestCase):
    def test_install_preserves_user_content_and_updates_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "AGENTS.md"
            path.write_text("# Repository rules\n\n- Keep this line.\n", encoding="utf-8")
            repository = VaultRepository(root / "vault.sqlite")
            profile = ProfileService(repository)
            claim = profile.add_candidate(attribute="identity.name", value="Simon")
            profile.confirm(claim.id)
            adapters = CliAdapterService(repository)

            first = adapters.install("codex", directory=root)
            second = adapters.install("codex", directory=root)

            content = path.read_text(encoding="utf-8")
            self.assertIn("Keep this line", content)
            self.assertIn("identity.name", content)
            self.assertEqual(content.count("contextvault:start"), 1)
            self.assertTrue(first["changed"])
            self.assertFalse(second["changed"])
            self.assertEqual(len(adapters.installations()), 1)

    def test_replaces_an_older_protocol_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "CLAUDE.md"
            path.write_text(
                "before\n\n<!-- contextvault:start protocol=1 -->\nold\n<!-- contextvault:end -->\n",
                encoding="utf-8",
            )
            repository = VaultRepository(root / "vault.sqlite")

            CliAdapterService(repository).install("claude-code", directory=root)

            content = path.read_text(encoding="utf-8")
            self.assertIn("before", content)
            self.assertIn("protocol=2", content)
            self.assertNotIn("\nold\n", content)


if __name__ == "__main__":
    unittest.main()
