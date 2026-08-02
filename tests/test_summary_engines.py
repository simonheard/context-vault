from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from contextvault.repository import VaultRepository
from contextvault.services import ProfileService
from contextvault.summary_engines import SummaryEngineService, _parse_model_result


class SummaryEngineTests(unittest.TestCase):
    def test_deterministic_engine_is_always_available(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = VaultRepository(Path(directory) / "vault.sqlite")
            profile = ProfileService(repository)
            claim = profile.add_candidate(attribute="identity.name", value="Simon")
            profile.confirm(claim.id)
            service = SummaryEngineService(repository)
            self.assertTrue(service.detect()[0]["available"])
            result = service.generate(engine="deterministic", summary_type="personal")
            self.assertIn("Simon", result["content"])

    def test_model_result_rejects_unknown_claim_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown claim"):
            _parse_model_result('{"summary":"Hello","claim_ids":["claim_wrong"]}', {"claim_ok"}, 1000)


if __name__ == "__main__":
    unittest.main()
