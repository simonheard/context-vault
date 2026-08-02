from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from contextvault.domain import (
    Claim,
    ClaimSource,
    ClaimStatus,
    Sensitivity,
    SourceType,
    utc_now,
)
from contextvault.repository import VaultRepository


class ProfileService:
    def __init__(self, repository: VaultRepository):
        self.repository = repository

    def add_candidate(
        self,
        *,
        attribute: str,
        value: Any,
        space: str = "personal",
        confidence: float = 1.0,
        sensitivity: Sensitivity = Sensitivity.PERSONAL,
        source_type: SourceType = SourceType.MANUAL,
        account_id: Optional[str] = None,
        platform: Optional[str] = None,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        evidence_hash: Optional[str] = None,
        valid_from: Optional[str] = None,
        valid_until: Optional[str] = None,
    ) -> Claim:
        profile_space = self.repository.get_space(space)
        entity_id = self.repository.ensure_user_entity()
        source = ClaimSource(
            source_type=source_type,
            observed_at=utc_now(),
            account_id=account_id,
            platform=platform,
            conversation_id=conversation_id,
            message_id=message_id,
            evidence_hash=evidence_hash,
        )
        return self.repository.add_claim(
            entity_id=entity_id,
            attribute=attribute,
            value=value,
            confidence=confidence,
            sensitivity=sensitivity,
            space_ids=[profile_space.id],
            source=source,
            valid_from=valid_from,
            valid_until=valid_until,
        )

    def confirm(self, claim_id: str) -> Claim:
        return self.repository.transition_claim(claim_id, ClaimStatus.CONFIRMED)

    def reject(self, claim_id: str) -> Claim:
        return self.repository.transition_claim(claim_id, ClaimStatus.REJECTED)

    def confirm_all(self, space: Optional[str] = None) -> list[Claim]:
        return [self.confirm(claim.id) for claim in self.candidates(space)]

    def health(self, space: str = "personal") -> dict[str, Any]:
        claims = self.repository.list_claims(space=space, limit=1000)
        counts = {status.value: 0 for status in ClaimStatus}
        for claim in claims:
            counts[claim.status.value] += 1
        confirmed = counts[ClaimStatus.CONFIRMED.value]
        sourced = sum(bool(self.repository.claim_sources(claim.id)) for claim in claims)
        score = 100 if not claims else round(
            100 * (0.6 * confirmed / len(claims) + 0.4 * sourced / len(claims))
        )
        return {
            "space": space,
            "score": score,
            "counts": counts,
            "without_source": len(claims) - sourced,
            "needs_review": counts["candidate"] + counts["conflicted"],
        }

    def candidates(self, space: Optional[str] = None) -> list[Claim]:
        return self.repository.list_claims(status=ClaimStatus.CANDIDATE, space=space)

    def current_claims(self, space: str = "personal") -> list[Claim]:
        return self.repository.list_claims(status=ClaimStatus.CONFIRMED, space=space)

    def current_profile(self, space: str = "personal") -> dict[str, Any]:
        claims = self.current_claims(space)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for claim in claims:
            category = claim.attribute.split(".", 1)[0]
            grouped[category].append(claim_to_dict(claim))
        return {
            "space": space,
            "categories": dict(sorted(grouped.items())),
            "claim_count": len(claims),
        }

    def markdown_profile(self, space: str = "personal") -> str:
        profile = self.current_profile(space)
        lines = [f"# ContextVault Profile: {space}", ""]
        if not profile["claim_count"]:
            return "\n".join(lines + ["No confirmed profile information.", ""])
        for category, claims in profile["categories"].items():
            lines.extend([f"## {category.title()}", ""])
            for claim in claims:
                lines.append(f"- **{claim['attribute']}**: {claim['value_text']}")
            lines.append("")
        return "\n".join(lines)


def claim_to_dict(claim: Claim) -> dict[str, Any]:
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
        "observed_at": claim.observed_at,
        "created_at": claim.created_at,
        "updated_at": claim.updated_at,
    }
