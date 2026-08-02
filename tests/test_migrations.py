from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from contextvault.vault import initialize


class MigrationTests(unittest.TestCase):
    def test_adds_route_id_to_an_existing_receipts_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "old.sqlite"
            with sqlite3.connect(path) as connection:
                connection.execute(
                    """
                    CREATE TABLE sync_receipts (
                        id TEXT PRIMARY KEY,
                        target_id TEXT NOT NULL,
                        profile_version TEXT NOT NULL,
                        manifest_json TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        completed_at TEXT
                    )
                    """
                )

            result = initialize(path)

            with sqlite3.connect(path) as connection:
                columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(sync_receipts)")
                }
            self.assertEqual(result.schema_version, 7)
            self.assertIn("route_id", columns)


if __name__ == "__main__":
    unittest.main()
