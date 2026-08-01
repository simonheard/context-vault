from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from aimem.cli import main
from aimem.vault import status


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
            self.assertEqual(status(vault_path).schema_version, 1)
            self.assertIn("Memories: 0", output.getvalue())

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
