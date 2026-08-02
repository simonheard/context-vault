from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from contextvault.domain import Sensitivity
from contextvault.security import find_secrets


@dataclass(frozen=True)
class ExtractedCandidate:
    attribute: str
    value: str
    confidence: float
    sensitivity: Sensitivity
    conversation_id: str
    message_id: str
    account_id: Optional[str]


_PATTERNS: list[tuple[str, re.Pattern[str], float, Sensitivity]] = [
    ("identity.name", re.compile(r"(?:my name is|call me)\s+([^,.!?\n]{2,60})", re.I), 0.98, Sensitivity.PERSONAL),
    ("identity.name", re.compile(r"(?:我叫|我的名字是)\s*([^，。！？\n]{1,30})"), 0.98, Sensitivity.PERSONAL),
    ("location.current.city", re.compile(r"I (?:currently )?live in\s+([^,.!?\n]{2,80})", re.I), 0.96, Sensitivity.PRIVATE),
    ("location.current.city", re.compile(r"我(?:现在)?住在\s*([^，。！？\n]{2,40})"), 0.96, Sensitivity.PRIVATE),
    ("employment.current.company", re.compile(r"I (?:currently )?work (?:at|for)\s+([^,.!?\n]{2,100})", re.I), 0.96, Sensitivity.PRIVATE),
    ("employment.current.company", re.compile(r"我(?:现在)?在\s*([^，。！？\n]{2,60}?)(?:工作|上班)"), 0.96, Sensitivity.PRIVATE),
    ("education.current.school", re.compile(r"I (?:study|am studying) at\s+([^,.!?\n]{2,100})", re.I), 0.95, Sensitivity.PRIVATE),
    ("education.current.school", re.compile(r"我(?:现在)?在\s*([^，。！？\n]{2,60}?)(?:上学|读书|学习)"), 0.95, Sensitivity.PRIVATE),
    ("identity.language", re.compile(r"I speak\s+([^.!?\n]{2,100})", re.I), 0.94, Sensitivity.PERSONAL),
    ("identity.language", re.compile(r"我会说\s*([^。！？\n]{2,60})"), 0.94, Sensitivity.PERSONAL),
    ("preference.response.style", re.compile(r"I prefer\s+([^.!?\n]{3,160})", re.I), 0.82, Sensitivity.PERSONAL),
    ("preference.response.style", re.compile(r"我(?:更)?喜欢\s*([^。！？\n]{3,100})"), 0.82, Sensitivity.PERSONAL),
    ("device.owned", re.compile(r"I (?:have|use|own) (?:an? )?([^,.!?\n]{2,100})", re.I), 0.75, Sensitivity.PRIVATE),
    ("device.owned", re.compile(r"我(?:有|使用)一?(?:台|部|个)?\s*([^，。！？\n]{2,60})"), 0.75, Sensitivity.PRIVATE),
]


def extract_profile_candidates(messages: Iterable[dict[str, object]]) -> list[ExtractedCandidate]:
    candidates: list[ExtractedCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    for message in messages:
        if message.get("role") != "user":
            continue
        content = str(message.get("content") or "")
        if find_secrets(content):
            continue
        for attribute, pattern, confidence, sensitivity in _PATTERNS:
            for match in pattern.finditer(content):
                value = _clean_value(match.group(1))
                key = (attribute, value.casefold(), str(message.get("provider_message_id") or ""))
                if not value or key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    ExtractedCandidate(
                        attribute=attribute,
                        value=value,
                        confidence=confidence,
                        sensitivity=sensitivity,
                        conversation_id=str(message.get("conversation_id") or ""),
                        message_id=str(message.get("provider_message_id") or ""),
                        account_id=(str(message["account_id"]) if message.get("account_id") else None),
                    )
                )
    return candidates


def _clean_value(value: str) -> str:
    return value.strip(" \t\r\n:：,，;；-—").strip()
