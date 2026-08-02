from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

from contextvault.domain import Claim, ClaimStatus, Sensitivity, utc_now
from contextvault.repository import VaultRepository


_SENSITIVITY_RANK = {
    Sensitivity.PUBLIC: 0,
    Sensitivity.PERSONAL: 1,
    Sensitivity.PRIVATE: 2,
    Sensitivity.SENSITIVE: 3,
    Sensitivity.SECRET: 4,
}


DEFAULT_POLICY: dict[str, Any] = {
    "allowed_categories": ["*"],
    "max_sensitivity": "personal",
    "sensitive_mode": "block",
    "category_modes": {},
    "summary_budget_chars": 12000,
    "require_preview": True,
    "auto_sync": False,
    "attachment_mode": "reference",
    "automation_mode": "manual",
    "automation_interval_minutes": 60,
    "automation_risk_acknowledged_at": None,
}


@dataclass(frozen=True)
class SyncPreview:
    route_id: str
    target_id: str
    target_platform: str
    target_label: str
    content: str
    included: list[dict[str, Any]]
    attachments: list[dict[str, Any]]
    blocked: list[dict[str, Any]]
    awaiting_confirmation: list[dict[str, Any]]
    diff: dict[str, list[dict[str, Any]]]


class SyncService:
    def __init__(self, repository: VaultRepository):
        self.repository = repository

    def add_route(
        self,
        *,
        source_account_id: Optional[str],
        space: str,
        target_account_id: str,
        policy: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        profile_space = self.repository.get_space(space)
        merged_policy = _validate_policy(policy or {})
        now = utc_now()
        target_id = f"target_{uuid4().hex}"
        route_id = f"route_{uuid4().hex}"
        with self.repository.transaction() as connection:
            target_account = connection.execute(
                "SELECT id FROM provider_accounts WHERE id = ? AND status = 'active'",
                (target_account_id,),
            ).fetchone()
            if target_account is None:
                raise ValueError("Target account is unknown or inactive")
            if source_account_id:
                source_account = connection.execute(
                    "SELECT id FROM provider_accounts WHERE id = ? AND status = 'active'",
                    (source_account_id,),
                ).fetchone()
                if source_account is None:
                    raise ValueError("Source account is unknown or inactive")
            connection.execute(
                "INSERT INTO sync_targets(id, account_id, enabled, policy_json) VALUES (?, ?, 1, ?)",
                (target_id, target_account_id, json.dumps(merged_policy, sort_keys=True)),
            )
            connection.execute(
                """
                INSERT INTO sync_routes(
                    id, source_account_id, space_id, target_id, enabled,
                    policy_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    route_id,
                    source_account_id,
                    profile_space.id,
                    target_id,
                    json.dumps(merged_policy, sort_keys=True),
                    now,
                    now,
                ),
            )
        self.repository.append_event(
            "route.created",
            "sync_route",
            route_id,
            {"source_account_id": source_account_id, "space": space, "target_id": target_id},
        )
        return {"id": route_id, "target_id": target_id, "policy": merged_policy}

    def list_routes(self) -> list[dict[str, Any]]:
        with self.repository.transaction() as connection:
            rows = connection.execute(
                """
                SELECT r.*, ps.name AS space_name,
                       source.account_label AS source_label,
                       target_account.account_label AS target_label,
                       target_account.platform AS target_platform,
                       t.last_synced_at
                FROM sync_routes r
                JOIN profile_spaces ps ON ps.id = r.space_id
                JOIN sync_targets t ON t.id = r.target_id
                JOIN provider_accounts target_account ON target_account.id = t.account_id
                LEFT JOIN provider_accounts source ON source.id = r.source_account_id
                ORDER BY r.created_at
                """
            ).fetchall()
        return [
            {
                **dict(row),
                "policy": json.loads(row["policy_json"]),
            }
            for row in rows
        ]

    def disable_route(self, route_id: str) -> None:
        self._route(route_id)
        with self.repository.transaction() as connection:
            connection.execute(
                "UPDATE sync_routes SET enabled = 0, updated_at = ? WHERE id = ?",
                (utc_now(), route_id),
            )
        self.repository.append_event(
            "route.disabled", "sync_route", route_id, {"enabled": False}
        )

    def configure_automation(
        self,
        route_id: str,
        *,
        enabled: bool,
        interval_minutes: int = 60,
        risk_acknowledged: bool = False,
    ) -> dict[str, Any]:
        route = self._route(route_id)
        if enabled and not risk_acknowledged:
            raise ValueError("Full automation requires explicit data-risk acknowledgement")
        if not 5 <= interval_minutes <= 10080:
            raise ValueError("Automation interval must be between 5 and 10080 minutes")
        policy = _validate_policy(json.loads(route["policy_json"]))
        policy["automation_mode"] = "full" if enabled else "manual"
        policy["automation_interval_minutes"] = interval_minutes
        policy["automation_risk_acknowledged_at"] = utc_now() if enabled else None
        with self.repository.transaction() as connection:
            connection.execute(
                "UPDATE sync_routes SET policy_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(policy, sort_keys=True), utc_now(), route_id),
            )
        self.repository.append_event(
            "route.automation_changed",
            "sync_route",
            route_id,
            {"enabled": enabled, "interval_minutes": interval_minutes},
        )
        return {"route_id": route_id, "automation": policy["automation_mode"], "interval_minutes": interval_minutes}

    def automation_jobs(self) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        for route in self.list_routes():
            if not route["enabled"]:
                continue
            policy = _validate_policy(route["policy"])
            if policy["automation_mode"] != "full" or not policy["automation_risk_acknowledged_at"]:
                continue
            if not _interval_due(route["last_synced_at"], int(policy["automation_interval_minutes"])):
                continue
            with self.repository.transaction() as connection:
                prepared = connection.execute(
                    "SELECT 1 FROM sync_receipts WHERE route_id = ? AND status = 'prepared' LIMIT 1",
                    (route["id"],),
                ).fetchone()
            if prepared:
                continue
            preview = self.preview(route["id"], approve_sensitive=False)
            changes = sum(len(items) for items in preview.diff.values())
            if not changes or preview.awaiting_confirmation:
                continue
            jobs.append(
                {
                    "route_id": route["id"],
                    "target_platform": route["target_platform"],
                    "target_label": route["target_label"],
                    "change_count": changes,
                }
            )
        return jobs

    def run_automation(self, route_id: str) -> dict[str, Any]:
        route = self._route(route_id)
        policy = _validate_policy(json.loads(route["policy_json"]))
        if policy["automation_mode"] != "full" or not policy["automation_risk_acknowledged_at"]:
            raise ValueError("Full automation is not enabled for this route")
        return self.run(route_id, approve_sensitive=False)

    def set_sensitive_sync(self, enabled: bool) -> None:
        with self.repository.transaction() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES ('sensitive_sync_enabled', ?)",
                ("1" if enabled else "0",),
            )
        self.repository.append_event(
            "privacy.sensitive_sync_changed",
            "privacy_policy",
            "global",
            {"enabled": enabled},
        )

    def record_consent(
        self, route_id: str, categories: list[str], mode: str, notice_version: str = "1"
    ) -> str:
        if mode not in {"ask", "allow"}:
            raise ValueError("Consent mode must be ask or allow")
        route = self._route(route_id)
        receipt_id = f"consent_{uuid4().hex}"
        with self.repository.transaction() as connection:
            connection.execute(
                """
                INSERT INTO consent_receipts(
                    id, target_id, policy_version, categories_json,
                    sensitivity_mode, notice_version, acknowledged_at
                ) VALUES (?, ?, '1', ?, ?, ?, ?)
                """,
                (receipt_id, route["target_id"], json.dumps(categories), mode, notice_version, utc_now()),
            )
        self.repository.append_event(
            "consent.granted", "consent_receipt", receipt_id, {"route_id": route_id, "mode": mode}
        )
        return receipt_id

    def revoke_consent(self, consent_id: str) -> None:
        now = utc_now()
        with self.repository.transaction() as connection:
            cursor = connection.execute(
                "UPDATE consent_receipts SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                (now, consent_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Unknown or already revoked consent receipt")
        self.repository.append_event(
            "consent.revoked", "consent_receipt", consent_id, {"revoked_at": now}
        )

    def preview(self, route_id: str, approve_sensitive: bool = False) -> SyncPreview:
        route = self._route(route_id)
        policy = _validate_policy(json.loads(route["policy_json"]))
        claims = self.repository.list_claims(
            status=ClaimStatus.CONFIRMED,
            space=route["space_name"],
            limit=1000,
        )
        global_sensitive = self._global_sensitive_enabled()
        included: list[dict[str, Any]] = []
        included_attachments: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        pending: list[dict[str, Any]] = []
        budget = int(policy["summary_budget_chars"])
        lines = [f"# ContextVault profile for {route['target_platform']}", ""]
        for claim in claims:
            item = _manifest_item(claim)
            reason = _blocked_reason(claim, policy)
            if reason:
                blocked.append({**item, "reason": reason})
                continue
            mode = _mode_for_claim(claim, policy)
            if claim.sensitivity in {Sensitivity.PRIVATE, Sensitivity.SENSITIVE}:
                if not global_sensitive:
                    blocked.append({**item, "reason": "global_sensitive_sync_disabled"})
                    continue
                if mode == "block":
                    blocked.append({**item, "reason": "policy_block"})
                    continue
                if mode == "ask" and not approve_sensitive:
                    pending.append(item)
                    continue
                if mode == "allow" and not self._has_active_consent(
                    route["target_id"], claim.attribute, "allow"
                ):
                    pending.append({**item, "reason": "consent_required"})
                    continue
            line = f"- {claim.attribute}: {claim.value_text}"
            if sum(len(part) + 1 for part in lines) + len(line) > budget:
                blocked.append({**item, "reason": "summary_budget"})
                continue
            lines.append(line)
            included.append(item)
        attachment_mode = policy["attachment_mode"]
        source_account_id = route.get("source_account_id")
        if attachment_mode != "exclude" and source_account_id:
            for attachment in self.repository.list_attachment_refs(source_account_id):
                item = {
                    "id": attachment.id,
                    "provider_file_id": attachment.provider_file_id,
                    "filename": attachment.filename,
                    "mime_type": attachment.mime_type,
                    "sensitivity": attachment.sensitivity.value,
                    "mode": attachment_mode,
                }
                maximum = Sensitivity(policy["max_sensitivity"])
                if _SENSITIVITY_RANK[attachment.sensitivity] > _SENSITIVITY_RANK[maximum]:
                    blocked.append({**item, "reason": "above_max_sensitivity"})
                    continue
                sensitivity_mode = str(
                    policy.get("category_modes", {}).get(
                        "attachment", policy["sensitive_mode"]
                    )
                )
                if attachment.sensitivity in {Sensitivity.PRIVATE, Sensitivity.SENSITIVE}:
                    if not global_sensitive:
                        blocked.append(
                            {**item, "reason": "global_sensitive_sync_disabled"}
                        )
                        continue
                    if sensitivity_mode == "block":
                        blocked.append({**item, "reason": "policy_block"})
                        continue
                    if sensitivity_mode == "ask" and not approve_sensitive:
                        pending.append(item)
                        continue
                    if sensitivity_mode == "allow" and not self._has_active_consent(
                        route["target_id"], "attachment", "allow"
                    ):
                        pending.append({**item, "reason": "consent_required"})
                        continue
                if attachment_mode == "transfer":
                    blocked.append({**item, "reason": "interactive_provider_adapter_required"})
                    continue
                if attachment_mode == "extracted_text" and not attachment.extracted_text:
                    blocked.append({**item, "reason": "no_approved_extracted_text"})
                    continue
                description = (
                    attachment.extracted_text
                    if attachment_mode == "extracted_text"
                    else attachment.description or "Provider-hosted file; content not copied"
                )
                line = f"- Attachment {attachment.filename}: {description}"
                if sum(len(part) + 1 for part in lines) + len(line) > budget:
                    blocked.append({**item, "reason": "summary_budget"})
                    continue
                lines.append(line)
                included_attachments.append(item)
        content = "\n".join(lines).rstrip() + "\n"
        diff = self._diff(route_id, included)
        return SyncPreview(
            route_id,
            route["target_id"],
            route["target_platform"],
            route["target_label"],
            content,
            included,
            included_attachments,
            blocked,
            pending,
            diff,
        )

    def run(self, route_id: str, approve_sensitive: bool = False) -> dict[str, Any]:
        preview = self.preview(route_id, approve_sensitive)
        if preview.awaiting_confirmation:
            raise ValueError("Sync contains fields that require confirmation")
        manifest = {
            "claims": preview.included,
            "attachments": preview.attachments,
            "diff": preview.diff,
        }
        canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True) + preview.content
        version = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        receipt_id = f"receipt_{uuid4().hex}"
        now = utc_now()
        with self.repository.transaction() as connection:
            connection.execute(
                """
                INSERT INTO sync_receipts(
                    id, target_id, route_id, profile_version, manifest_json,
                    status, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, 'prepared', ?, NULL)
                """,
                (
                    receipt_id,
                    preview.target_id,
                    route_id,
                    version,
                    json.dumps(manifest, ensure_ascii=False, sort_keys=True),
                    now,
                ),
            )
        self.repository.append_event(
            "sync.prepared",
            "sync_receipt",
            receipt_id,
            {"route_id": route_id, "version": version, "claim_count": len(preview.included)},
        )
        return {
            "id": receipt_id,
            "version": version,
            "target": preview.target_label,
            "content": preview.content,
            "manifest": manifest,
        }

    def acknowledge(self, receipt_id: str) -> dict[str, Any]:
        now = utc_now()
        with self.repository.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM sync_receipts WHERE id = ?", (receipt_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Unknown sync receipt")
            if row["status"] == "completed":
                return dict(row)
            if row["status"] != "prepared":
                raise ValueError("Only a prepared receipt can be acknowledged")
            connection.execute(
                "UPDATE sync_receipts SET status = 'completed', completed_at = ? WHERE id = ?",
                (now, receipt_id),
            )
            connection.execute(
                "UPDATE sync_targets SET last_synced_at = ? WHERE id = ?",
                (now, row["target_id"]),
            )
        self.repository.append_event(
            "sync.completed", "sync_receipt", receipt_id, {"completed_at": now}
        )
        return next(item for item in self.list_receipts() if item["id"] == receipt_id)

    def fail_receipt(self, receipt_id: str, reason: str) -> dict[str, Any]:
        now = utc_now()
        with self.repository.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM sync_receipts WHERE id = ?", (receipt_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Unknown sync receipt")
            if row["status"] != "prepared":
                raise ValueError("Only a prepared receipt can be marked failed")
            connection.execute(
                "UPDATE sync_receipts SET status = 'failed', completed_at = ? WHERE id = ?",
                (now, receipt_id),
            )
        self.repository.append_event(
            "sync.failed",
            "sync_receipt",
            receipt_id,
            {"failed_at": now, "reason": reason[:300]},
        )
        return next(item for item in self.list_receipts() if item["id"] == receipt_id)

    def list_receipts(self) -> list[dict[str, Any]]:
        with self.repository.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM sync_receipts ORDER BY created_at DESC"
            ).fetchall()
        return [{**dict(row), "manifest": json.loads(row["manifest_json"])} for row in rows]

    def _route(self, route_id: str) -> dict[str, Any]:
        with self.repository.transaction() as connection:
            row = connection.execute(
                """
                SELECT r.*, ps.name AS space_name, t.account_id,
                       a.platform AS target_platform, a.account_label AS target_label
                FROM sync_routes r
                JOIN profile_spaces ps ON ps.id = r.space_id
                JOIN sync_targets t ON t.id = r.target_id
                JOIN provider_accounts a ON a.id = t.account_id
                WHERE r.id = ? AND r.enabled = 1 AND t.enabled = 1
                """,
                (route_id,),
            ).fetchone()
        if row is None:
            raise ValueError("Unknown or disabled sync route")
        return dict(row)

    def _global_sensitive_enabled(self) -> bool:
        with self.repository.transaction() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'sensitive_sync_enabled'"
            ).fetchone()
        return bool(row and row[0] == "1")

    def _has_active_consent(
        self, target_id: str, attribute: str, required_mode: str
    ) -> bool:
        with self.repository.transaction() as connection:
            rows = connection.execute(
                """
                SELECT categories_json, sensitivity_mode FROM consent_receipts
                WHERE target_id = ? AND revoked_at IS NULL ORDER BY acknowledged_at DESC
                """,
                (target_id,),
            ).fetchall()
        category = attribute.split(".", 1)[0]
        for row in rows:
            categories = json.loads(row["categories_json"])
            mode_matches = row["sensitivity_mode"] == required_mode
            category_matches = "*" in categories or category in categories or attribute in categories
            if mode_matches and category_matches:
                return True
        return False

    def _diff(self, route_id: str, current: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        with self.repository.transaction() as connection:
            row = connection.execute(
                "SELECT manifest_json FROM sync_receipts WHERE route_id = ? AND status = 'completed' ORDER BY created_at DESC LIMIT 1",
                (route_id,),
            ).fetchone()
        previous = json.loads(row[0]).get("claims", []) if row else []
        old = {item["id"]: item for item in previous}
        new = {item["id"]: item for item in current}
        return {
            "added": [item for key, item in new.items() if key not in old],
            "changed": [item for key, item in new.items() if key in old and item != old[key]],
            "removed": [item for key, item in old.items() if key not in new],
        }


def _validate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    merged = {**DEFAULT_POLICY, **policy}
    if merged["max_sensitivity"] not in {item.value for item in Sensitivity if item is not Sensitivity.SECRET}:
        raise ValueError("Invalid maximum sensitivity")
    if merged["sensitive_mode"] not in {"block", "ask", "allow"}:
        raise ValueError("Invalid sensitive mode")
    budget = int(merged["summary_budget_chars"])
    if not 200 <= budget <= 100000:
        raise ValueError("Summary budget must be between 200 and 100000 characters")
    merged["summary_budget_chars"] = budget
    if merged["attachment_mode"] not in {
        "exclude",
        "reference",
        "extracted_text",
        "transfer",
    }:
        raise ValueError("Invalid attachment mode")
    if merged["automation_mode"] not in {"manual", "full"}:
        raise ValueError("Invalid automation mode")
    interval = int(merged["automation_interval_minutes"])
    if not 5 <= interval <= 10080:
        raise ValueError("Invalid automation interval")
    merged["automation_interval_minutes"] = interval
    return merged


def _blocked_reason(claim: Claim, policy: dict[str, Any]) -> Optional[str]:
    category = claim.attribute.split(".", 1)[0]
    allowed = policy["allowed_categories"]
    if "*" not in allowed and not any(
        claim.attribute == value or claim.attribute.startswith(f"{value}.") or category == value
        for value in allowed
    ):
        return "category_not_allowed"
    maximum = Sensitivity(policy["max_sensitivity"])
    if _SENSITIVITY_RANK[claim.sensitivity] > _SENSITIVITY_RANK[maximum]:
        return "above_max_sensitivity"
    return None


def _mode_for_claim(claim: Claim, policy: dict[str, Any]) -> str:
    modes = policy.get("category_modes", {})
    category = claim.attribute.split(".", 1)[0]
    return str(modes.get(claim.attribute, modes.get(category, policy["sensitive_mode"])))


def _manifest_item(claim: Claim) -> dict[str, Any]:
    return {
        "id": claim.id,
        "attribute": claim.attribute,
        "value": claim.value,
        "value_text": claim.value_text,
        "sensitivity": claim.sensitivity.value,
        "updated_at": claim.updated_at,
    }


def _interval_due(last_synced_at: Optional[str], interval_minutes: int) -> bool:
    if not last_synced_at:
        return True
    try:
        last = datetime.fromisoformat(last_synced_at)
    except ValueError:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    elapsed = datetime.now(timezone.utc) - last
    return elapsed.total_seconds() >= interval_minutes * 60
