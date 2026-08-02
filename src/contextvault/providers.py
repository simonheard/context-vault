from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProviderCapability:
    id: str
    display_name: str
    hostnames: tuple[str, ...]
    page_injection: bool
    file_import: bool
    attachment_transfer: bool
    notes: str


PROVIDERS = {
    "chatgpt": ProviderCapability(
        "chatgpt",
        "ChatGPT",
        ("chatgpt.com", "chat.openai.com"),
        True,
        True,
        False,
        "Fills the logged-in composer; the user reviews and sends.",
    ),
    "gemini": ProviderCapability(
        "gemini",
        "Gemini",
        ("gemini.google.com",),
        True,
        True,
        False,
        "Fills the logged-in composer; the user reviews and sends.",
    ),
    "claude": ProviderCapability(
        "claude",
        "Claude",
        ("claude.ai",),
        True,
        True,
        False,
        "Fills the logged-in composer; the user reviews and sends.",
    ),
}


def provider_capabilities() -> list[dict[str, object]]:
    return [asdict(item) for item in PROVIDERS.values()]
