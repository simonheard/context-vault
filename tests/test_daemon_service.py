from __future__ import annotations

import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from contextvault.daemon_service import daemon_status, install_daemon, uninstall_daemon


class DaemonServiceTests(unittest.TestCase):
    @patch("contextvault.daemon_service.platform.system", return_value="Darwin")
    def test_macos_definition_is_loopback_only_and_removable(self, _system) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = install_daemon(
                home / "vault.sqlite", home=home, activate=False
            )
            path = Path(str(result["path"]))
            payload = plistlib.loads(path.read_bytes())

            self.assertTrue(daemon_status(home)["installed"])
            self.assertIn("127.0.0.1", payload["ProgramArguments"])
            removed = uninstall_daemon(home, deactivate=False)
            self.assertFalse(removed["installed"])
            self.assertFalse(path.exists())

    @patch("contextvault.daemon_service.platform.system", return_value="Linux")
    def test_linux_definition_uses_user_systemd_service(self, _system) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = install_daemon(
                home / "vault.sqlite", home=home, activate=False
            )
            content = Path(str(result["path"])).read_text(encoding="utf-8")
            self.assertIn("ExecStart=", content)
            self.assertIn("contextvault", content)


if __name__ == "__main__":
    unittest.main()
