from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class ImportedMessage:
    conversation_id: str
    conversation_title: str
    message_id: str
    role: str
    content: str
    created_at: Optional[str] = None


@dataclass(frozen=True)
class ImportBundle:
    source_name: str
    source_hash: str
    conversation_count: int
    messages: list[ImportedMessage]


def load_chatgpt_export(path: Path) -> ImportBundle:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Export does not exist: {path}")
    raw = path.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            candidates = [name for name in archive.namelist() if name.endswith("conversations.json")]
            if not candidates:
                raise ValueError("ChatGPT export does not contain conversations.json")
            payload = json.loads(archive.read(sorted(candidates, key=len)[0]))
    else:
        payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError("conversations.json must contain a list")
    messages: list[ImportedMessage] = []
    conversation_ids: set[str] = set()
    for index, conversation in enumerate(payload):
        if not isinstance(conversation, dict):
            continue
        conversation_id = str(conversation.get("id") or conversation.get("conversation_id") or index)
        title = str(conversation.get("title") or "Untitled conversation")
        conversation_ids.add(conversation_id)
        messages.extend(_messages_from_conversation(conversation, conversation_id, title))
    return ImportBundle(path.name, source_hash, len(conversation_ids), messages)


def _messages_from_conversation(
    conversation: dict[str, Any], conversation_id: str, title: str
) -> Iterable[ImportedMessage]:
    mapping = conversation.get("mapping")
    if isinstance(mapping, dict):
        nodes = sorted(
            mapping.values(),
            key=lambda node: _sort_time(node.get("message") if isinstance(node, dict) else None),
        )
        for node in nodes:
            if not isinstance(node, dict):
                continue
            message = node.get("message")
            parsed = _parse_message(message, conversation_id, title)
            if parsed:
                yield parsed
        return
    messages = conversation.get("messages")
    if isinstance(messages, list):
        for message in messages:
            parsed = _parse_message(message, conversation_id, title)
            if parsed:
                yield parsed


def _parse_message(
    message: Any, conversation_id: str, title: str
) -> Optional[ImportedMessage]:
    if not isinstance(message, dict):
        return None
    author = message.get("author")
    role = author.get("role") if isinstance(author, dict) else message.get("role")
    if role not in {"user", "assistant", "system", "tool"}:
        return None
    content_value = message.get("content")
    if isinstance(content_value, dict):
        parts = content_value.get("parts", [])
        content = "\n".join(str(part) for part in parts if isinstance(part, (str, int, float)))
    else:
        content = str(content_value or message.get("text") or "")
    content = content.strip()
    if not content:
        return None
    created = message.get("create_time") or message.get("created_at")
    return ImportedMessage(
        conversation_id=conversation_id,
        conversation_title=title,
        message_id=str(message.get("id") or hashlib.sha256(content.encode()).hexdigest()[:24]),
        role=str(role),
        content=content,
        created_at=str(created) if created is not None else None,
    )


def _sort_time(message: Any) -> tuple[bool, float]:
    if not isinstance(message, dict):
        return (True, 0)
    value = message.get("create_time")
    try:
        return (value is None, float(value or 0))
    except (TypeError, ValueError):
        return (True, 0)
