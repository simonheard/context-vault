from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from contextvault.domain import ClaimStatus, SourceType
from contextvault.extractors import extract_profile_candidates
from contextvault.importers import load_chatgpt_export
from contextvault.repository import VaultRepository
from contextvault.services import ProfileService


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
        evidence = self.repository.list_evidence_messages(import_id, "user")
        candidates = extract_profile_candidates(evidence)
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
                platform="chatgpt",
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
