from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


SCHEMA_VERSION = 2


@dataclass(frozen=True)
class VaultStatus:
    path: Path
    schema_version: int
    claim_count: int
    device_count: int
    sync_target_count: int


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

            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                display_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                attribute TEXT NOT NULL,
                value_json TEXT NOT NULL,
                value_text TEXT NOT NULL,
                confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
                status TEXT NOT NULL DEFAULT 'candidate',
                sensitivity TEXT NOT NULL DEFAULT 'private',
                valid_from TEXT,
                valid_until TEXT,
                observed_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS claim_sources (
                id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                source_type TEXT NOT NULL,
                platform TEXT,
                conversation_id TEXT,
                message_id TEXT,
                device_scan_id TEXT,
                evidence_hash TEXT,
                observed_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL UNIQUE REFERENCES entities(id) ON DELETE CASCADE,
                device_type TEXT NOT NULL,
                fingerprint TEXT,
                last_seen_at TEXT,
                config_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS sync_targets (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                account_label TEXT,
                enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                policy_json TEXT NOT NULL DEFAULT '{}',
                last_synced_at TEXT
            );

            CREATE TABLE IF NOT EXISTS sync_receipts (
                id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL REFERENCES sync_targets(id) ON DELETE CASCADE,
                profile_version TEXT NOT NULL,
                manifest_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(
                claim_id UNINDEXED,
                attribute,
                value_text
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
        claim_row = connection.execute("SELECT COUNT(*) FROM claims").fetchone()
        device_row = connection.execute("SELECT COUNT(*) FROM devices").fetchone()
        target_row = connection.execute("SELECT COUNT(*) FROM sync_targets").fetchone()
    if None in (version_row, claim_row, device_row, target_row):
        raise ValueError(f"Not a valid ContextVault vault: {path}")
    return VaultStatus(
        path,
        int(version_row[0]),
        int(claim_row[0]),
        int(device_row[0]),
        int(target_row[0]),
    )
