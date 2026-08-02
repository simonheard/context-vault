from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from contextvault.domain import utc_now
from contextvault.pipeline import ImportPipeline
from contextvault.providers import PROVIDERS
from contextvault.repository import VaultRepository


class CaptureService:
    """Manage user-approved capture from already authenticated provider pages."""

    def __init__(self, repository: VaultRepository):
        self.repository = repository

    def configure(
        self,
        account_id: str,
        *,
        enabled: bool,
        interval_minutes: int = 15,
        risk_acknowledged: bool = False,
        conversation_url: str | None = None,
    ) -> dict[str, Any]:
        if enabled and not risk_acknowledged:
            raise ValueError("Automatic conversation capture requires explicit privacy-risk acknowledgement")
        if not 5 <= interval_minutes <= 10080:
            raise ValueError("Capture interval must be between 5 and 10080 minutes")
        account = self.repository.get_account(account_id)
        if account.platform not in PROVIDERS:
            raise ValueError("Automatic capture requires a registered web provider")
        now = utc_now()
        with self.repository.transaction() as connection:
            existing = connection.execute(
                "SELECT id, created_at FROM capture_sources WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            capture_id = str(existing["id"]) if existing else f"capture_{uuid4().hex}"
            created_at = str(existing["created_at"]) if existing else now
            connection.execute(
                """
                INSERT INTO capture_sources(
                    id, account_id, enabled, interval_minutes, risk_acknowledged_at,
                    conversation_url, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    enabled = excluded.enabled,
                    interval_minutes = excluded.interval_minutes,
                    risk_acknowledged_at = excluded.risk_acknowledged_at,
                    conversation_url = COALESCE(excluded.conversation_url, capture_sources.conversation_url),
                    consecutive_failures = 0,
                    paused_reason = NULL,
                    updated_at = excluded.updated_at
                """,
                (
                    capture_id,
                    account_id,
                    int(enabled),
                    interval_minutes,
                    now if enabled else None,
                    _safe_provider_url(account.platform, conversation_url),
                    created_at,
                    now,
                ),
            )
        self.repository.append_event(
            "capture.configuration_changed",
            "capture_source",
            capture_id,
            {"account_id": account_id, "enabled": enabled, "interval_minutes": interval_minutes},
        )
        return self.get(account_id)

    def get(self, account_id: str) -> dict[str, Any]:
        with self.repository.transaction() as connection:
            row = connection.execute(
                """
                SELECT c.*, a.platform, a.account_label
                FROM capture_sources c JOIN provider_accounts a ON a.id = c.account_id
                WHERE c.account_id = ?
                """,
                (account_id,),
            ).fetchone()
        if row is None:
            return {"account_id": account_id, "enabled": 0, "interval_minutes": 15}
        return dict(row)

    def list(self) -> list[dict[str, Any]]:
        with self.repository.transaction() as connection:
            rows = connection.execute(
                """
                SELECT c.*, a.platform, a.account_label
                FROM capture_sources c JOIN provider_accounts a ON a.id = c.account_id
                ORDER BY c.created_at
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def jobs(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self.list()
            if item["enabled"]
            and item["risk_acknowledged_at"]
            and not item["paused_reason"]
            and _interval_due(item["last_captured_at"], int(item["interval_minutes"]))
        ]

    def ingest(
        self,
        account_id: str,
        *,
        provider: str,
        conversation_url: str,
        title: str,
        messages: list[dict[str, object]],
        space: str = "personal",
        knowledge_probe: bool = False,
    ) -> dict[str, Any]:
        account = self.repository.get_account(account_id)
        if account.platform != provider:
            raise ValueError("Captured provider does not match the configured source account")
        safe_url = _safe_provider_url(provider, conversation_url)
        result = ImportPipeline(self.repository).import_browser_capture(
            provider=provider,
            account_id=account_id,
            conversation_url=safe_url or PROVIDERS[provider].start_url,
            title=title,
            messages=messages,
            space=space,
            knowledge_probe=knowledge_probe,
        )
        now = utc_now()
        with self.repository.transaction() as connection:
            connection.execute(
                """
                UPDATE capture_sources
                SET last_captured_at = ?, conversation_url = ?, consecutive_failures = 0,
                    paused_reason = NULL, updated_at = ?
                WHERE account_id = ?
                """,
                (now, safe_url, now, account_id),
            )
        self.repository.append_event(
            "capture.completed",
            "provider_account",
            account_id,
            {"provider": provider, "messages": result.messages, "candidates": result.candidates},
        )
        return result.__dict__

    def record_failure(self, account_id: str, reason: str) -> dict[str, Any]:
        now = utc_now()
        with self.repository.transaction() as connection:
            row = connection.execute(
                "SELECT consecutive_failures FROM capture_sources WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Capture is not configured for this account")
            failures = int(row[0]) + 1
            paused = "three_consecutive_adapter_failures" if failures >= 3 else None
            connection.execute(
                "UPDATE capture_sources SET consecutive_failures = ?, paused_reason = ?, updated_at = ? WHERE account_id = ?",
                (failures, paused, now, account_id),
            )
        self.repository.append_event(
            "capture.failed", "provider_account", account_id,
            {"reason": reason[:300], "consecutive_failures": failures, "paused": bool(paused)},
        )
        return self.get(account_id)


def _safe_provider_url(provider: str, value: str | None) -> str | None:
    if not value:
        return None
    from urllib.parse import urlparse

    parsed = urlparse(value)
    capability = PROVIDERS.get(provider)
    if parsed.scheme != "https" or not capability or parsed.hostname not in capability.hostnames:
        raise ValueError("Conversation URL must use the configured provider's HTTPS hostname")
    return value[:2000]


def _interval_due(last_at: str | None, interval_minutes: int) -> bool:
    if not last_at:
        return True
    try:
        last = datetime.fromisoformat(last_at)
    except ValueError:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last).total_seconds() >= interval_minutes * 60
