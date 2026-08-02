from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Optional

from contextvault.domain import ClaimStatus, Sensitivity, SourceType
from contextvault.extractors import extract_profile_candidates
from contextvault.importers import ImportBundle, ImportedMessage, load_chatgpt_export
from contextvault.repository import VaultRepository
from contextvault.services import ProfileService
from contextvault.security import reject_secrets


_SINGLE_VALUE_ATTRIBUTES = {
    "identity.name",
    "location.current.city",
    "employment.current.company",
    "education.current.school",
}


@dataclass(frozen=True)
class PipelineResult:
    import_id: str
    conversations: int
    messages: int
    candidates: int
    duplicates: int
    conflicts: int


class ImportPipeline:
    def __init__(self, repository: VaultRepository):
        self.repository = repository
        self.profile = ProfileService(repository)

    def import_chatgpt(
        self,
        path: Path,
        *,
        account_id: Optional[str] = None,
        space: str = "personal",
        extract: bool = True,
    ) -> PipelineResult:
        bundle = load_chatgpt_export(path)
        imported = self.repository.store_import(bundle, account_id)
        return self._extract_import(imported, account_id, space, "chatgpt", extract)

    def import_browser_capture(
        self,
        *,
        provider: str,
        account_id: str,
        conversation_url: str,
        title: str,
        messages: list[dict[str, object]],
        space: str = "personal",
        extract: bool = True,
        knowledge_probe: bool = False,
    ) -> PipelineResult:
        if not 1 <= len(messages) <= 2000:
            raise ValueError("A browser capture must contain between 1 and 2000 messages")
        normalized: list[ImportedMessage] = []
        total_chars = 0
        conversation_id = hashlib.sha256(conversation_url.encode()).hexdigest()[:24]
        for index, item in enumerate(messages):
            role = str(item.get("role", ""))
            content = str(item.get("content", "")).strip()
            if role not in {"user", "assistant"} or not content:
                continue
            total_chars += len(content)
            if total_chars > 2_000_000:
                raise ValueError("Browser capture exceeds the two-million-character limit")
            message_id = str(item.get("id") or hashlib.sha256(f"{role}\0{content}\0{index}".encode()).hexdigest()[:24])
            normalized.append(
                ImportedMessage(
                    conversation_id=conversation_id,
                    conversation_title=title[:200] or "Captured conversation",
                    message_id=message_id[:200],
                    role=role,
                    content=content,
                    created_at=str(item.get("created_at")) if item.get("created_at") else None,
                )
            )
        if not normalized:
            raise ValueError("Browser capture contains no supported messages")
        canonical = json.dumps(
            [{"id": item.message_id, "role": item.role, "content": item.content} for item in normalized],
            ensure_ascii=False,
            sort_keys=True,
        )
        bundle = ImportBundle(
            source_name=f"{provider} browser: {title[:120]}",
            source_hash=hashlib.sha256(f"{provider}\0{account_id}\0{canonical}".encode()).hexdigest(),
            conversation_count=1,
            messages=normalized,
            source_type=f"{provider}_browser_capture",
        )
        imported = self.repository.store_import(bundle, account_id)
        return self._extract_import(
            imported,
            account_id,
            space,
            provider,
            extract,
            extract_role="assistant" if knowledge_probe else "user",
            confidence_scale=0.65 if knowledge_probe else 1.0,
        )

    def import_standalone_vault(self, path: Path, *, space: str = "personal") -> dict[str, int]:
        """Import an explicit JSON backup from the independent browser extension."""
        if path.stat().st_size > 5_000_000:
            raise ValueError("Standalone browser backup exceeds the five-megabyte limit")
        raw = path.read_bytes()
        payload = json.loads(raw)
        return self.import_standalone_payload(
            payload, space=space, backup_hash=hashlib.sha256(raw).hexdigest()
        )

    def import_standalone_payload(
        self, payload: object, *, space: str = "personal", backup_hash: str | None = None
    ) -> dict[str, int]:
        if not isinstance(payload, dict) or payload.get("schema") != 1:
            raise ValueError("Unsupported standalone browser backup schema")
        items = payload.get("claims")
        if not isinstance(items, list) or len(items) > 10000:
            raise ValueError("Standalone browser backup has an invalid claim list")
        for item in items:
            if isinstance(item, dict) and item.get("status") != "rejected":
                value = str(item.get("value", "")).strip()
                if value:
                    reject_secrets(value)
        service = ProfileService(self.repository)
        existing = {(item.attribute, item.value_text) for item in self.repository.list_claims(space=space, limit=1000)}
        added = confirmed = skipped = 0
        backup_hash = backup_hash or hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        for item in items:
            if not isinstance(item, dict) or item.get("status") == "rejected":
                skipped += 1
                continue
            attribute = str(item.get("attribute", "")).strip()
            value = str(item.get("value", "")).strip()
            if not attribute or not value or (attribute, value) in existing:
                skipped += 1
                continue
            sensitivity_value = str(item.get("sensitivity", "personal"))
            sensitivity = Sensitivity(sensitivity_value) if sensitivity_value in {entry.value for entry in Sensitivity if entry is not Sensitivity.SECRET} else Sensitivity.PERSONAL
            claim = service.add_candidate(
                attribute=attribute,
                value=value,
                space=space,
                confidence=max(0.0, min(1.0, float(item.get("confidence", 1.0)))),
                sensitivity=sensitivity,
                source_type=SourceType.IMPORT,
                platform="browser_extension",
                evidence_hash=backup_hash,
            )
            added += 1
            existing.add((attribute, value))
            if item.get("status") == "confirmed":
                service.confirm(claim.id)
                confirmed += 1
        self.repository.append_event(
            "browser_backup.imported", "standalone_backup", backup_hash[:24],
            {"added": added, "confirmed": confirmed, "skipped": skipped},
        )
        return {"added": added, "confirmed": confirmed, "skipped": skipped}

    def _extract_import(
        self,
        imported: dict[str, object],
        account_id: Optional[str],
        space: str,
        platform: str,
        extract: bool,
        extract_role: str = "user",
        confidence_scale: float = 1.0,
    ) -> PipelineResult:
        import_id = str(imported["id"])
        if not extract:
            return PipelineResult(
                import_id,
                int(imported["conversation_count"]),
                int(imported["message_count"]),
                0,
                0,
                0,
            )
        evidence = self.repository.list_evidence_messages(import_id, extract_role)
        candidates = extract_profile_candidates(
            evidence, roles={extract_role}, confidence_scale=confidence_scale
        )
        added = duplicates = conflicts = 0
        existing = self.repository.list_claims(space=space, limit=1000)
        for candidate in candidates:
            same_attribute = [item for item in existing if item.attribute == candidate.attribute]
            if any(item.value_text.casefold() == candidate.value.casefold() for item in same_attribute):
                duplicates += 1
                continue
            claim = self.profile.add_candidate(
                attribute=candidate.attribute,
                value=candidate.value,
                space=space,
                confidence=candidate.confidence,
                sensitivity=candidate.sensitivity,
                source_type=SourceType.IMPORT,
                account_id=candidate.account_id or account_id,
                platform=platform,
                conversation_id=candidate.conversation_id,
                message_id=candidate.message_id,
            )
            conflicting = [
                item
                for item in same_attribute
                if candidate.attribute in _SINGLE_VALUE_ATTRIBUTES
                and item.status in {ClaimStatus.CANDIDATE, ClaimStatus.CONFIRMED}
            ]
            if conflicting:
                for old_claim in conflicting:
                    self.repository.transition_claim(old_claim.id, ClaimStatus.CONFLICTED)
                self.repository.transition_claim(claim.id, ClaimStatus.CONFLICTED)
                conflicts += 1
            added += 1
            existing.append(claim)
        return PipelineResult(
            import_id,
            int(imported["conversation_count"]),
            int(imported["message_count"]),
            added,
            duplicates,
            conflicts,
        )
