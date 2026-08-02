from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone


SCHEMA_VERSION = 7


@dataclass(frozen=True)
class VaultStatus:
    path: Path
    schema_version: int
    claim_count: int
    device_count: int
    account_count: int
    profile_space_count: int
    sync_route_count: int
    sync_target_count: int
    attachment_count: int
    sync_event_count: int


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

            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
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
                account_id TEXT REFERENCES provider_accounts(id) ON DELETE SET NULL,
                source_type TEXT NOT NULL,
                platform TEXT,
                conversation_id TEXT,
                message_id TEXT,
                device_scan_id TEXT,
                evidence_hash TEXT,
                observed_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS provider_accounts (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                account_label TEXT NOT NULL,
                external_account_hash TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(platform, account_label)
            );

            CREATE TABLE IF NOT EXISTS profile_spaces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS claim_spaces (
                claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                space_id TEXT NOT NULL REFERENCES profile_spaces(id) ON DELETE CASCADE,
                PRIMARY KEY (claim_id, space_id)
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
                account_id TEXT NOT NULL REFERENCES provider_accounts(id) ON DELETE CASCADE,
                enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                policy_json TEXT NOT NULL DEFAULT '{}',
                last_synced_at TEXT
            );

            CREATE TABLE IF NOT EXISTS sync_routes (
                id TEXT PRIMARY KEY,
                source_account_id TEXT REFERENCES provider_accounts(id) ON DELETE SET NULL,
                space_id TEXT NOT NULL REFERENCES profile_spaces(id) ON DELETE CASCADE,
                target_id TEXT NOT NULL REFERENCES sync_targets(id) ON DELETE CASCADE,
                enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                policy_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sync_receipts (
                id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL REFERENCES sync_targets(id) ON DELETE CASCADE,
                route_id TEXT REFERENCES sync_routes(id) ON DELETE SET NULL,
                profile_version TEXT NOT NULL,
                manifest_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS consent_receipts (
                id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL REFERENCES sync_targets(id) ON DELETE CASCADE,
                policy_version TEXT NOT NULL,
                categories_json TEXT NOT NULL,
                sensitivity_mode TEXT NOT NULL,
                notice_version TEXT NOT NULL,
                acknowledged_at TEXT NOT NULL,
                revoked_at TEXT
            );

            CREATE TABLE IF NOT EXISTS attachment_refs (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL REFERENCES provider_accounts(id) ON DELETE CASCADE,
                provider_file_id TEXT NOT NULL,
                conversation_id TEXT,
                message_id TEXT,
                remote_url TEXT,
                filename TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER,
                sha256 TEXT,
                description TEXT,
                extracted_text TEXT,
                sensitivity TEXT NOT NULL DEFAULT 'private',
                status TEXT NOT NULL DEFAULT 'active',
                last_verified_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(account_id, provider_file_id)
            );

            CREATE TABLE IF NOT EXISTS sync_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                device_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                aggregate_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS device_sync_cursors (
                device_id TEXT PRIMARY KEY,
                last_sequence INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS source_imports (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                account_id TEXT REFERENCES provider_accounts(id) ON DELETE SET NULL,
                source_name TEXT NOT NULL,
                source_hash TEXT NOT NULL UNIQUE,
                conversation_count INTEGER NOT NULL DEFAULT 0,
                message_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS evidence_messages (
                id TEXT PRIMARY KEY,
                import_id TEXT NOT NULL REFERENCES source_imports(id) ON DELETE CASCADE,
                account_id TEXT REFERENCES provider_accounts(id) ON DELETE SET NULL,
                conversation_id TEXT NOT NULL,
                conversation_title TEXT,
                provider_message_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT,
                imported_at TEXT NOT NULL,
                UNIQUE(import_id, conversation_id, provider_message_id, content_hash)
            );

            CREATE TABLE IF NOT EXISTS generated_summaries (
                id TEXT PRIMARY KEY,
                space_id TEXT NOT NULL REFERENCES profile_spaces(id) ON DELETE CASCADE,
                target_id TEXT REFERENCES sync_targets(id) ON DELETE SET NULL,
                summary_type TEXT NOT NULL,
                version TEXT NOT NULL,
                content TEXT NOT NULL,
                manifest_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(
                claim_id UNINDEXED,
                attribute,
                value_text
            );

            CREATE TRIGGER IF NOT EXISTS claims_fts_insert AFTER INSERT ON claims BEGIN
                INSERT INTO claims_fts(claim_id, attribute, value_text)
                VALUES (new.id, new.attribute, new.value_text);
            END;

            CREATE TRIGGER IF NOT EXISTS claims_fts_update AFTER UPDATE OF attribute, value_text ON claims BEGIN
                DELETE FROM claims_fts WHERE claim_id = old.id;
                INSERT INTO claims_fts(claim_id, attribute, value_text)
                VALUES (new.id, new.attribute, new.value_text);
            END;

            CREATE TRIGGER IF NOT EXISTS claims_fts_delete AFTER DELETE ON claims BEGIN
                DELETE FROM claims_fts WHERE claim_id = old.id;
            END;

            CREATE INDEX IF NOT EXISTS claims_status_updated_idx
                ON claims(status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS claim_sources_claim_idx
                ON claim_sources(claim_id);
            CREATE INDEX IF NOT EXISTS sync_events_device_sequence_idx
                ON sync_events(device_id, sequence);
            CREATE INDEX IF NOT EXISTS attachment_refs_account_status_idx
                ON attachment_refs(account_id, status);
            CREATE INDEX IF NOT EXISTS evidence_messages_import_role_idx
                ON evidence_messages(import_id, role);
            CREATE INDEX IF NOT EXISTS generated_summaries_space_created_idx
                ON generated_summaries(space_id, created_at DESC);
            """
        )
        _ensure_column(
            connection,
            "sync_receipts",
            "route_id",
            "TEXT REFERENCES sync_routes(id) ON DELETE SET NULL",
        )
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        now = datetime.now(timezone.utc).isoformat()
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (SCHEMA_VERSION, now),
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO profile_spaces(
                id, name, display_name, is_default, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("space_personal", "personal", "Personal", 1, now, now),
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
        account_row = connection.execute(
            "SELECT COUNT(*) FROM provider_accounts"
        ).fetchone()
        space_row = connection.execute("SELECT COUNT(*) FROM profile_spaces").fetchone()
        route_row = connection.execute("SELECT COUNT(*) FROM sync_routes").fetchone()
        target_row = connection.execute("SELECT COUNT(*) FROM sync_targets").fetchone()
        attachment_row = connection.execute("SELECT COUNT(*) FROM attachment_refs").fetchone()
        event_row = connection.execute("SELECT COUNT(*) FROM sync_events").fetchone()
    if None in (
        version_row,
        claim_row,
        device_row,
        account_row,
        space_row,
        route_row,
        target_row,
        attachment_row,
        event_row,
    ):
        raise ValueError(f"Not a valid ContextVault vault: {path}")
    return VaultStatus(
        path,
        int(version_row[0]),
        int(claim_row[0]),
        int(device_row[0]),
        int(account_row[0]),
        int(space_row[0]),
        int(route_row[0]),
        int(target_row[0]),
        int(attachment_row[0]),
        int(event_row[0]),
    )


def _ensure_column(
    connection: sqlite3.Connection, table: str, column: str, declaration: str
) -> None:
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
