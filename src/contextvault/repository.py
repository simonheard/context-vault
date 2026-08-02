from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import secrets
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional
from uuid import uuid4

from contextvault.domain import (
    AttachmentRef,
    Claim,
    ClaimSource,
    ClaimStatus,
    ProfileSpace,
    ProviderAccount,
    Sensitivity,
    SourceType,
    SyncEvent,
    utc_now,
)
from contextvault.vault import initialize
from contextvault.importers import ImportBundle, ImportedMessage
from contextvault.security import find_secrets, reject_secrets
from contextvault.providers import PROVIDERS
from contextvault.protocol import PROTOCOL_VERSION, check_protocol


class VaultRepository:
    def __init__(self, path: Path):
        self.path = initialize(path).path

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def extension_pairing_token(self) -> str:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'extension_pairing_token'"
            ).fetchone()
        if row is None:
            raise ValueError("Extension pairing token is unavailable")
        return str(row[0])

    def rotate_extension_pairing_token(self) -> str:
        token = secrets.token_urlsafe(32)
        with self.transaction() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES ('extension_pairing_token', ?)",
                (token,),
            )
            connection.execute("UPDATE sync_clients SET token_hash = NULL, status = 'revoked'")
            self._append_event(
                connection,
                "extension.pairing_token_rotated",
                "extension_pairing",
                "local",
                {},
            )
        return token

    def create_link_code(self, ttl_seconds: int = 600) -> dict[str, Any]:
        if not 60 <= ttl_seconds <= 3600:
            raise ValueError("Link-code lifetime must be between 60 and 3600 seconds")
        code = f"{secrets.randbelow(100_000_000):08d}"
        digest = hashlib.sha256(f"{self.extension_pairing_token()}:{code}".encode()).hexdigest()
        payload = {"hash": digest, "expires_at": int(time.time()) + ttl_seconds, "attempts": 0}
        with self.transaction() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES ('extension_link_code', ?)",
                (json.dumps(payload, sort_keys=True),),
            )
        return {"code": code, "expires_at": payload["expires_at"]}

    def exchange_link_code(
        self, code: str, client_id: str, client_version: str, protocol_version: int
    ) -> dict[str, Any]:
        if len(code) != 8 or not code.isdigit():
            raise ValueError("Link code must contain eight digits")
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'extension_link_code'"
            ).fetchone()
            if row is None:
                raise ValueError("No active link code; run contextvault link")
            payload = json.loads(row[0])
            if int(payload.get("expires_at", 0)) < int(time.time()):
                connection.execute("DELETE FROM metadata WHERE key = 'extension_link_code'")
                raise ValueError("Link code expired; run contextvault link again")
            attempts = int(payload.get("attempts", 0)) + 1
            expected = str(payload.get("hash", ""))
            supplied = hashlib.sha256(f"{self.extension_pairing_token()}:{code}".encode()).hexdigest()
            if attempts > 5 or not hmac.compare_digest(supplied, expected):
                if attempts >= 5:
                    connection.execute("DELETE FROM metadata WHERE key = 'extension_link_code'")
                else:
                    payload["attempts"] = attempts
                    connection.execute(
                        "UPDATE metadata SET value = ? WHERE key = 'extension_link_code'",
                        (json.dumps(payload, sort_keys=True),),
                    )
                raise ValueError("Link code is invalid")
            connection.execute("DELETE FROM metadata WHERE key = 'extension_link_code'")
        return self.register_client(
            client_id, "chrome-extension", client_version, protocol_version
        )

    def add_account(self, platform: str, label: str) -> ProviderAccount:
        platform = platform.strip().lower()
        label = label.strip()
        if platform not in {*PROVIDERS, "other"}:
            raise ValueError("Unsupported provider")
        if not 1 <= len(label) <= 80:
            raise ValueError("Account label must be between 1 and 80 characters")
        now = utc_now()
        account = ProviderAccount(
            id=f"account_{uuid4().hex}",
            platform=platform,
            account_label=label,
            status="active",
            created_at=now,
            updated_at=now,
        )
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO provider_accounts(
                    id, platform, account_label, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    account.id,
                    account.platform,
                    account.account_label,
                    account.status,
                    account.created_at,
                    account.updated_at,
                ),
            )
            self._append_event(
                connection, "account.created", "provider_account", account.id, _account_dict(account)
            )
        return account

    def list_accounts(self) -> list[ProviderAccount]:
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM provider_accounts ORDER BY created_at"
            ).fetchall()
        return [_account_from_row(row) for row in rows]

    def get_account(self, account_id: str) -> ProviderAccount:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM provider_accounts WHERE id = ?", (account_id,)
            ).fetchone()
        if row is None:
            raise ValueError("Unknown provider account")
        return _account_from_row(row)

    def update_account(
        self, account_id: str, *, label: Optional[str] = None, status: Optional[str] = None
    ) -> ProviderAccount:
        if status is not None and status not in {"active", "disconnected", "revoked"}:
            raise ValueError("Invalid account status")
        if label is not None and not 1 <= len(label.strip()) <= 80:
            raise ValueError("Account label must be between 1 and 80 characters")
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM provider_accounts WHERE id = ?", (account_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Unknown provider account")
            new_label = label.strip() if label is not None else row["account_label"]
            new_status = status or row["status"]
            now = utc_now()
            connection.execute(
                "UPDATE provider_accounts SET account_label = ?, status = ?, updated_at = ? WHERE id = ?",
                (new_label, new_status, now, account_id),
            )
            if new_status != "active":
                connection.execute(
                    "UPDATE sync_targets SET enabled = 0 WHERE account_id = ?", (account_id,)
                )
                connection.execute(
                    "UPDATE sync_routes SET enabled = 0, updated_at = ? WHERE source_account_id = ?",
                    (now, account_id),
                )
                connection.execute(
                    "UPDATE capture_sources SET enabled = 0, updated_at = ? WHERE account_id = ?",
                    (now, account_id),
                )
            self._append_event(
                connection,
                "account.updated",
                "provider_account",
                account_id,
                {"label": new_label, "status": new_status},
            )
        return next(item for item in self.list_accounts() if item.id == account_id)

    def add_attachment_ref(
        self,
        *,
        account_id: str,
        provider_file_id: str,
        filename: str,
        remote_url: Optional[str] = None,
        mime_type: Optional[str] = None,
        size_bytes: Optional[int] = None,
        description: Optional[str] = None,
        extracted_text: Optional[str] = None,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        sha256: Optional[str] = None,
    ) -> AttachmentRef:
        provider_file_id = provider_file_id.strip()
        filename = filename.strip()
        if not provider_file_id:
            raise ValueError("Provider file ID must not be empty")
        if not filename:
            raise ValueError("Filename must not be empty")
        if size_bytes is not None and size_bytes < 0:
            raise ValueError("Attachment size must not be negative")
        if sensitivity is Sensitivity.SECRET:
            raise ValueError("Secret-class data must not be stored")
        if extracted_text:
            reject_secrets(extracted_text)
        now = utc_now()
        attachment = AttachmentRef(
            id=f"attachment_{uuid4().hex}",
            account_id=account_id,
            provider_file_id=provider_file_id,
            filename=filename,
            remote_url=remote_url,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            description=description,
            extracted_text=extracted_text,
            sensitivity=sensitivity,
            status="active",
            conversation_id=conversation_id,
            message_id=message_id,
            created_at=now,
            updated_at=now,
        )
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO attachment_refs(
                    id, account_id, provider_file_id, conversation_id, message_id,
                    remote_url, filename, mime_type, size_bytes, sha256,
                    description, extracted_text, sensitivity, status,
                    last_verified_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attachment.id,
                    attachment.account_id,
                    attachment.provider_file_id,
                    attachment.conversation_id,
                    attachment.message_id,
                    attachment.remote_url,
                    attachment.filename,
                    attachment.mime_type,
                    attachment.size_bytes,
                    attachment.sha256,
                    attachment.description,
                    attachment.extracted_text,
                    attachment.sensitivity.value,
                    attachment.status,
                    attachment.last_verified_at,
                    attachment.created_at,
                    attachment.updated_at,
                ),
            )
            self._append_event(
                connection,
                "attachment.created",
                "attachment_ref",
                attachment.id,
                _attachment_dict(attachment),
            )
        return attachment

    def list_attachment_refs(
        self, account_id: Optional[str] = None
    ) -> list[AttachmentRef]:
        query = "SELECT * FROM attachment_refs"
        parameters: tuple[str, ...] = ()
        if account_id is not None:
            query += " WHERE account_id = ?"
            parameters = (account_id,)
        query += " ORDER BY created_at"
        with self.transaction() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [_attachment_from_row(row) for row in rows]

    def store_import(
        self, bundle: ImportBundle, account_id: Optional[str] = None
    ) -> dict[str, Any]:
        with self.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM source_imports WHERE source_hash = ?",
                (bundle.source_hash,),
            ).fetchone()
            if existing is not None:
                return dict(existing)
            import_id = f"import_{uuid4().hex}"
            now = utc_now()
            connection.execute(
                """
                INSERT INTO source_imports(
                    id, source_type, account_id, source_name, source_hash,
                    conversation_count, message_count, status, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)
                """,
                (
                    import_id,
                    bundle.source_type,
                    account_id,
                    bundle.source_name,
                    bundle.source_hash,
                    bundle.conversation_count,
                    len(bundle.messages),
                    now,
                    now,
                ),
            )
            for message in bundle.messages:
                self._insert_evidence_message(connection, import_id, account_id, message, now)
            payload = {
                "source_name": bundle.source_name,
                "conversation_count": bundle.conversation_count,
                "message_count": len(bundle.messages),
            }
            self._append_event(connection, "import.completed", "source_import", import_id, payload)
            return {"id": import_id, "status": "completed", **payload}

    def list_imports(self) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM source_imports ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def list_evidence_messages(
        self, import_id: str, role: Optional[str] = None
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM evidence_messages WHERE import_id = ?"
        parameters: list[Any] = [import_id]
        if role is not None:
            query += " AND role = ?"
            parameters.append(role)
        query += " ORDER BY created_at, id"
        with self.transaction() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]

    def _insert_evidence_message(
        self,
        connection: sqlite3.Connection,
        import_id: str,
        account_id: Optional[str],
        message: ImportedMessage,
        imported_at: str,
    ) -> None:
        content = message.content
        secret_matches = find_secrets(content)
        if secret_matches:
            kinds = ",".join(sorted({item.kind for item in secret_matches}))
            content = f"[REDACTED: secret-class content ({kinds})]"
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        connection.execute(
            """
            INSERT OR IGNORE INTO evidence_messages(
                id, import_id, account_id, conversation_id, conversation_title,
                provider_message_id, role, content, content_hash, created_at, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"evidence_{uuid4().hex}",
                import_id,
                account_id,
                message.conversation_id,
                message.conversation_title,
                message.message_id,
                message.role,
                content,
                content_hash,
                message.created_at,
                imported_at,
            ),
        )

    def add_space(self, name: str, display_name: str) -> ProfileSpace:
        name = name.strip().lower().replace(" ", "-")
        display_name = display_name.strip()
        if not name or not all(character.isalnum() or character in "-_" for character in name):
            raise ValueError("Space name may contain letters, numbers, hyphens, and underscores")
        if not 1 <= len(display_name) <= 80:
            raise ValueError("Display name must be between 1 and 80 characters")
        now = utc_now()
        space = ProfileSpace(
            id=f"space_{uuid4().hex}",
            name=name,
            display_name=display_name,
            is_default=False,
            created_at=now,
            updated_at=now,
        )
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO profile_spaces(
                    id, name, display_name, is_default, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (space.id, space.name, space.display_name, 0, now, now),
            )
            self._append_event(
                connection, "space.created", "profile_space", space.id, _space_dict(space)
            )
        return space

    def list_spaces(self) -> list[ProfileSpace]:
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM profile_spaces ORDER BY is_default DESC, created_at"
            ).fetchall()
        return [_space_from_row(row) for row in rows]

    def get_space(self, name_or_id: str) -> ProfileSpace:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM profile_spaces WHERE id = ? OR name = ?",
                (name_or_id, name_or_id),
            ).fetchone()
        if row is None:
            raise ValueError(f"Unknown profile space: {name_or_id}")
        return _space_from_row(row)

    def ensure_user_entity(self) -> str:
        now = utc_now()
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT id FROM entities WHERE kind = 'user' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is not None:
                return str(row[0])
            entity_id = f"entity_{uuid4().hex}"
            connection.execute(
                "INSERT INTO entities(id, kind, display_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (entity_id, "user", "User", now, now),
            )
            self._append_event(
                connection,
                "entity.created",
                "entity",
                entity_id,
                {"kind": "user", "display_name": "User"},
            )
            return entity_id

    def add_claim(
        self,
        *,
        entity_id: str,
        attribute: str,
        value: Any,
        value_text: Optional[str] = None,
        confidence: float = 1.0,
        status: ClaimStatus = ClaimStatus.CANDIDATE,
        sensitivity: Sensitivity = Sensitivity.PERSONAL,
        space_ids: Optional[list[str]] = None,
        source: Optional[ClaimSource] = None,
        valid_from: Optional[str] = None,
        valid_until: Optional[str] = None,
    ) -> Claim:
        attribute = attribute.strip()
        if not attribute or len(attribute) > 160:
            raise ValueError("Claim attribute must be between 1 and 160 characters")
        if not 0 <= confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        if sensitivity is Sensitivity.SECRET:
            raise ValueError("Secret-class data must not be stored")
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
        text = (value_text if value_text is not None else str(value)).strip()
        if not text:
            raise ValueError("Claim value must not be empty")
        reject_secrets(text)
        now = utc_now()
        observed_at = source.observed_at if source else now
        claim = Claim(
            id=f"claim_{uuid4().hex}",
            entity_id=entity_id,
            attribute=attribute,
            value=value,
            value_text=text,
            confidence=confidence,
            status=status,
            sensitivity=sensitivity,
            observed_at=observed_at,
            created_at=now,
            updated_at=now,
            valid_from=valid_from,
            valid_until=valid_until,
        )
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO claims(
                    id, entity_id, attribute, value_json, value_text, confidence,
                    status, sensitivity, valid_from, valid_until, observed_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim.id,
                    claim.entity_id,
                    claim.attribute,
                    serialized,
                    claim.value_text,
                    claim.confidence,
                    claim.status.value,
                    claim.sensitivity.value,
                    claim.valid_from,
                    claim.valid_until,
                    claim.observed_at,
                    claim.created_at,
                    claim.updated_at,
                ),
            )
            for space_id in space_ids or ["space_personal"]:
                connection.execute(
                    "INSERT INTO claim_spaces(claim_id, space_id) VALUES (?, ?)",
                    (claim.id, space_id),
                )
            if source is not None:
                connection.execute(
                    """
                    INSERT INTO claim_sources(
                        id, claim_id, account_id, source_type, platform,
                        conversation_id, message_id, device_scan_id, evidence_hash,
                        observed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"source_{uuid4().hex}",
                        claim.id,
                        source.account_id,
                        source.source_type.value,
                        source.platform,
                        source.conversation_id,
                        source.message_id,
                        source.device_scan_id,
                        source.evidence_hash,
                        source.observed_at,
                    ),
                )
            self._append_event(
                connection, "claim.created", "claim", claim.id, _claim_dict(claim)
            )
        return claim

    def get_claim(self, claim_id: str) -> Claim:
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
        if row is None:
            raise ValueError(f"Unknown claim: {claim_id}")
        return _claim_from_row(row)

    def list_claims(
        self,
        *,
        status: Optional[ClaimStatus] = None,
        space: Optional[str] = None,
        limit: int = 200,
    ) -> list[Claim]:
        if not 1 <= limit <= 1000:
            raise ValueError("Limit must be between 1 and 1000")
        parameters: list[Any] = []
        where: list[str] = []
        joins = ""
        if status is not None:
            where.append("c.status = ?")
            parameters.append(status.value)
        if space is not None:
            joins = " JOIN claim_spaces cs ON cs.claim_id = c.id JOIN profile_spaces ps ON ps.id = cs.space_id "
            where.append("(ps.id = ? OR ps.name = ?)")
            parameters.extend([space, space])
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        parameters.append(limit)
        with self.transaction() as connection:
            rows = connection.execute(
                f"SELECT DISTINCT c.* FROM claims c {joins}{clause} ORDER BY c.updated_at DESC LIMIT ?",
                parameters,
            ).fetchall()
        return [_claim_from_row(row) for row in rows]

    def search_claims(self, query: str, limit: int = 50) -> list[Claim]:
        query = query.strip()
        if not query:
            return []
        with self.transaction() as connection:
            rows = connection.execute(
                """
                SELECT c.* FROM claims_fts f
                JOIN claims c ON c.id = f.claim_id
                WHERE claims_fts MATCH ? ORDER BY rank LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        return [_claim_from_row(row) for row in rows]

    def claim_sources(self, claim_id: str) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM claim_sources WHERE claim_id = ? ORDER BY observed_at",
                (claim_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_claim(self, claim_id: str) -> None:
        claim = self.get_claim(claim_id)
        with self.transaction() as connection:
            connection.execute("DELETE FROM claims WHERE id = ?", (claim_id,))
            self._append_event(
                connection,
                "claim.deleted",
                "claim",
                claim_id,
                {"attribute": claim.attribute},
            )

    def transition_claim(self, claim_id: str, status: ClaimStatus) -> Claim:
        current = self.get_claim(claim_id)
        allowed = {
            ClaimStatus.CANDIDATE: {
                ClaimStatus.CONFIRMED,
                ClaimStatus.REJECTED,
                ClaimStatus.CONFLICTED,
                ClaimStatus.DELETED,
            },
            ClaimStatus.CONFIRMED: {
                ClaimStatus.SUPERSEDED,
                ClaimStatus.EXPIRED,
                ClaimStatus.CONFLICTED,
                ClaimStatus.DELETED,
            },
            ClaimStatus.CONFLICTED: {
                ClaimStatus.CONFIRMED,
                ClaimStatus.REJECTED,
                ClaimStatus.DELETED,
            },
        }
        if status not in allowed.get(current.status, set()):
            raise ValueError(f"Cannot transition claim from {current.status.value} to {status.value}")
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                "UPDATE claims SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, now, claim_id),
            )
            self._append_event(
                connection,
                f"claim.{status.value}",
                "claim",
                claim_id,
                {"previous_status": current.status.value, "status": status.value},
            )
        return self.get_claim(claim_id)

    def list_events(self, after_sequence: int = 0, limit: int = 200) -> list[SyncEvent]:
        with self.transaction() as connection:
            rows = connection.execute(
                """
                SELECT * FROM sync_events
                WHERE sequence > ? ORDER BY sequence LIMIT ?
                """,
                (after_sequence, limit),
            ).fetchall()
        return [_event_from_row(row) for row in rows]

    def get_cursor(self, device_id: str) -> int:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT last_sequence FROM device_sync_cursors WHERE device_id = ?",
                (device_id,),
            ).fetchone()
        return int(row[0]) if row else 0

    def set_cursor(self, device_id: str, sequence: int) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO device_sync_cursors(device_id, last_sequence, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    last_sequence = excluded.last_sequence,
                    updated_at = excluded.updated_at
                """,
                (device_id, sequence, utc_now()),
            )

    def upsert_device_scan(self, scan: dict[str, Any]) -> dict[str, Any]:
        fingerprint = str(scan["fingerprint"])
        now = utc_now()
        with self.transaction() as connection:
            existing = connection.execute(
                "SELECT d.*, e.display_name FROM devices d JOIN entities e ON e.id = d.entity_id WHERE d.fingerprint = ?",
                (fingerprint,),
            ).fetchone()
            config_json = json.dumps(scan["config"], ensure_ascii=False, sort_keys=True)
            if existing is None:
                entity_id = f"entity_{uuid4().hex}"
                device_id = f"device_{uuid4().hex}"
                connection.execute(
                    "INSERT INTO entities(id, kind, display_name, created_at, updated_at) VALUES (?, 'device', ?, ?, ?)",
                    (entity_id, scan["display_name"], now, now),
                )
                connection.execute(
                    "INSERT INTO devices(id, entity_id, device_type, fingerprint, last_seen_at, config_json) VALUES (?, ?, ?, ?, ?, ?)",
                    (device_id, entity_id, scan["device_type"], fingerprint, now, config_json),
                )
                event_type = "device.created"
                previous_config: dict[str, Any] = {}
            else:
                device_id = str(existing["id"])
                previous_config = json.loads(existing["config_json"])
                connection.execute(
                    "UPDATE devices SET device_type = ?, last_seen_at = ?, config_json = ? WHERE id = ?",
                    (scan["device_type"], now, config_json, device_id),
                )
                connection.execute(
                    "UPDATE entities SET display_name = ?, updated_at = ? WHERE id = ?",
                    (scan["display_name"], now, existing["entity_id"]),
                )
                event_type = "device.updated"
            changed = {
                key: {"before": previous_config.get(key), "after": value}
                for key, value in scan["config"].items()
                if previous_config.get(key) != value
            }
            self._append_event(
                connection,
                event_type,
                "device",
                device_id,
                {"display_name": scan["display_name"], "changes": changed},
            )
        return {"id": device_id, **scan, "last_seen_at": now, "changes": changed}

    def list_devices(self) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            rows = connection.execute(
                """
                SELECT d.*, e.display_name FROM devices d
                JOIN entities e ON e.id = d.entity_id ORDER BY d.last_seen_at DESC
                """
            ).fetchall()
        return [
            {
                "id": row["id"],
                "display_name": row["display_name"],
                "device_type": row["device_type"],
                "fingerprint": row["fingerprint"],
                "last_seen_at": row["last_seen_at"],
                "config": json.loads(row["config_json"]),
            }
            for row in rows
        ]

    def append_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
    ) -> None:
        with self.transaction() as connection:
            self._append_event(connection, event_type, aggregate_type, aggregate_id, payload)

    def register_client(
        self,
        client_id: str,
        client_type: str,
        client_version: str,
        protocol_version: int,
    ) -> dict[str, Any]:
        client_id = client_id.strip()
        client_type = client_type.strip()
        client_version = client_version.strip()
        if not 1 <= len(client_id) <= 128:
            raise ValueError("Client ID must be between 1 and 128 characters")
        if not 1 <= len(client_type) <= 80:
            raise ValueError("Client type must be between 1 and 80 characters")
        if not 1 <= len(client_version) <= 80:
            raise ValueError("Client version must be between 1 and 80 characters")
        if protocol_version < 1:
            raise ValueError("Protocol version must be positive")
        compatibility = check_protocol(protocol_version)
        client_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(client_token.encode()).hexdigest()
        now = utc_now()
        status = "active" if compatibility.compatible else "incompatible"
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO sync_clients(
                    id, client_type, client_version, protocol_version, status, token_hash, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    client_type = excluded.client_type,
                    client_version = excluded.client_version,
                    protocol_version = excluded.protocol_version,
                    status = excluded.status,
                    token_hash = excluded.token_hash,
                    last_seen_at = excluded.last_seen_at
                """,
                (client_id, client_type, client_version, protocol_version, status, token_hash, now),
            )
        return {
            "id": client_id,
            "status": status,
            "compatibility": compatibility.__dict__,
            "last_seen_at": now,
            "client_token": client_token,
        }

    def authorize_local_token(self, token: str) -> bool:
        if not token:
            return False
        enrollment = self.extension_pairing_token()
        if hmac.compare_digest(token, enrollment):
            return True
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT 1 FROM sync_clients WHERE token_hash = ? AND status = 'active'",
                (token_hash,),
            ).fetchone()
        return row is not None

    def list_clients(self) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM sync_clients ORDER BY last_seen_at DESC"
            ).fetchall()
        return [{key: row[key] for key in row.keys() if key != "token_hash"} for row in rows]

    def revoke_client(self, client_id: str) -> None:
        with self.transaction() as connection:
            cursor = connection.execute(
                "UPDATE sync_clients SET status = 'revoked', token_hash = NULL WHERE id = ?",
                (client_id,),
            )
            if cursor.rowcount != 1:
                raise ValueError("Unknown sync client")

    def _append_event(
        self,
        connection: sqlite3.Connection,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        device_id: str = "local",
    ) -> None:
        connection.execute(
            """
            INSERT INTO sync_events(
                event_id, device_id, event_type, aggregate_type, aggregate_id,
                payload_json, protocol_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"event_{uuid4().hex}",
                device_id,
                event_type,
                aggregate_type,
                aggregate_id,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                PROTOCOL_VERSION,
                utc_now(),
            ),
        )


def _account_from_row(row: sqlite3.Row) -> ProviderAccount:
    return ProviderAccount(
        id=row["id"],
        platform=row["platform"],
        account_label=row["account_label"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        external_account_hash=row["external_account_hash"],
    )


def _space_from_row(row: sqlite3.Row) -> ProfileSpace:
    return ProfileSpace(
        id=row["id"],
        name=row["name"],
        display_name=row["display_name"],
        is_default=bool(row["is_default"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _claim_from_row(row: sqlite3.Row) -> Claim:
    return Claim(
        id=row["id"],
        entity_id=row["entity_id"],
        attribute=row["attribute"],
        value=json.loads(row["value_json"]),
        value_text=row["value_text"],
        confidence=float(row["confidence"]),
        status=ClaimStatus(row["status"]),
        sensitivity=Sensitivity(row["sensitivity"]),
        observed_at=row["observed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        valid_from=row["valid_from"],
        valid_until=row["valid_until"],
    )


def _event_from_row(row: sqlite3.Row) -> SyncEvent:
    return SyncEvent(
        sequence=int(row["sequence"]),
        event_id=row["event_id"],
        device_id=row["device_id"],
        event_type=row["event_type"],
        aggregate_type=row["aggregate_type"],
        aggregate_id=row["aggregate_id"],
        payload=json.loads(row["payload_json"]),
        created_at=row["created_at"],
    )


def _attachment_from_row(row: sqlite3.Row) -> AttachmentRef:
    return AttachmentRef(
        id=row["id"],
        account_id=row["account_id"],
        provider_file_id=row["provider_file_id"],
        filename=row["filename"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        conversation_id=row["conversation_id"],
        message_id=row["message_id"],
        remote_url=row["remote_url"],
        mime_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        sha256=row["sha256"],
        description=row["description"],
        extracted_text=row["extracted_text"],
        sensitivity=Sensitivity(row["sensitivity"]),
        last_verified_at=row["last_verified_at"],
    )


def _account_dict(account: ProviderAccount) -> dict[str, Any]:
    return {
        "id": account.id,
        "platform": account.platform,
        "account_label": account.account_label,
        "status": account.status,
    }


def _space_dict(space: ProfileSpace) -> dict[str, Any]:
    return {
        "id": space.id,
        "name": space.name,
        "display_name": space.display_name,
        "is_default": space.is_default,
    }


def _claim_dict(claim: Claim) -> dict[str, Any]:
    return {
        "id": claim.id,
        "entity_id": claim.entity_id,
        "attribute": claim.attribute,
        "value": claim.value,
        "value_text": claim.value_text,
        "confidence": claim.confidence,
        "status": claim.status.value,
        "sensitivity": claim.sensitivity.value,
        "valid_from": claim.valid_from,
        "valid_until": claim.valid_until,
    }


def _attachment_dict(attachment: AttachmentRef) -> dict[str, Any]:
    return {
        "id": attachment.id,
        "account_id": attachment.account_id,
        "provider_file_id": attachment.provider_file_id,
        "filename": attachment.filename,
        "remote_url": attachment.remote_url,
        "mime_type": attachment.mime_type,
        "size_bytes": attachment.size_bytes,
        "sensitivity": attachment.sensitivity.value,
        "status": attachment.status,
    }
