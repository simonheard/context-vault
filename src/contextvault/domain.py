from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClaimStatus(str, Enum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    REJECTED = "rejected"
    CONFLICTED = "conflicted"
    DELETED = "deleted"


class Sensitivity(str, Enum):
    PUBLIC = "public"
    PERSONAL = "personal"
    PRIVATE = "private"
    SENSITIVE = "sensitive"
    SECRET = "secret"


class SourceType(str, Enum):
    MANUAL = "manual"
    CONVERSATION = "conversation"
    DEVICE_SCAN = "device_scan"
    IMPORT = "import"


@dataclass(frozen=True)
class ProviderAccount:
    id: str
    platform: str
    account_label: str
    status: str
    created_at: str
    updated_at: str
    external_account_hash: Optional[str] = None


@dataclass(frozen=True)
class ProfileSpace:
    id: str
    name: str
    display_name: str
    is_default: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ClaimSource:
    source_type: SourceType
    observed_at: str
    account_id: Optional[str] = None
    platform: Optional[str] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    device_scan_id: Optional[str] = None
    evidence_hash: Optional[str] = None


@dataclass(frozen=True)
class Claim:
    id: str
    entity_id: str
    attribute: str
    value: Any
    value_text: str
    confidence: float
    status: ClaimStatus
    sensitivity: Sensitivity
    observed_at: str
    created_at: str
    updated_at: str
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None


@dataclass(frozen=True)
class AttachmentRef:
    id: str
    account_id: str
    provider_file_id: str
    filename: str
    status: str
    created_at: str
    updated_at: str
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    remote_url: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None
    description: Optional[str] = None
    extracted_text: Optional[str] = None
    sensitivity: Sensitivity = Sensitivity.PRIVATE
    last_verified_at: Optional[str] = None


@dataclass(frozen=True)
class SyncEvent:
    sequence: int
    event_id: str
    device_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, Any]
    created_at: str
