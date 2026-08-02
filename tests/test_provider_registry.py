from __future__ import annotations

import re
import unittest
from pathlib import Path

from contextvault.providers import PROVIDERS


class ProviderRegistryTests(unittest.TestCase):
    def test_browser_and_server_provider_ids_match(self) -> None:
        source = (Path(__file__).parents[1] / "extension" / "providers.js").read_text()
        browser_ids = set(re.findall(r"^  ([a-z][a-z0-9-]*): \{", source, re.MULTILINE))
        self.assertEqual(browser_ids, set(PROVIDERS))


if __name__ == "__main__":
    unittest.main()
