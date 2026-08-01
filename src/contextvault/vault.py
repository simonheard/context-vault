from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class VaultStatus:
    path: Path
    schema_version: int
    memory_count: int


def initialize(path: Path) -> VaultStatus:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            PRAGMA journal_mode = WAL;
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                source_platform TEXT NOT NULL,
                source_conversation_id TEXT,
                source_message_id TEXT,
                scope TEXT NOT NULL DEFAULT 'global',
                confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
                valid_from TEXT,
                valid_until TEXT,
                sensitivity TEXT NOT NULL DEFAULT 'low',
                state TEXT NOT NULL DEFAULT 'candidate',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                memory_id UNINDEXED,
                content,
                subject,
                scope
            );
            """
        )
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
    return status(path)


def status(path: Path) -> VaultStatus:
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Vault does not exist: {path}")
    with sqlite3.connect(path) as connection:
        version_row = connection.execute(
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ).fetchone()
        count_row = connection.execute("SELECT COUNT(*) FROM memories").fetchone()
    if version_row is None or count_row is None:
        raise ValueError(f"Not a valid ContextVault vault: {path}")
    return VaultStatus(path, int(version_row[0]), int(count_row[0]))

