from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretMatch:
    kind: str
    preview: str


_SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "api_key": re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|glpat-[A-Za-z0-9_-]{20,}|npm_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{20,})\b"
    ),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}", re.IGNORECASE),
    "password_assignment": re.compile(
        r"\b(?:password|passwd|pwd|api[_-]?key|secret|token)\s*[:=]\s*\S{8,}",
        re.IGNORECASE,
    ),
    "cookie": re.compile(r"\b(?:sessionid|auth_token|set-cookie)\s*[:=]", re.IGNORECASE),
}


def find_secrets(text: str) -> list[SecretMatch]:
    matches: list[SecretMatch] = []
    for kind, pattern in _SECRET_PATTERNS.items():
        match = pattern.search(text)
        if match:
            value = match.group(0)
            matches.append(SecretMatch(kind, f"{value[:4]}…{value[-2:]}"))
    return matches


def reject_secrets(text: str) -> None:
    matches = find_secrets(text)
    if matches:
        kinds = ", ".join(sorted({item.kind for item in matches}))
        raise ValueError(f"Secret-class content rejected: {kinds}")
