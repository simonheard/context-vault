from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import uuid4

from contextvault.domain import utc_now
from contextvault.repository import VaultRepository
from contextvault.summaries import SummaryService


@dataclass(frozen=True)
class CliTool:
    id: str
    display_name: str
    project_path: str
    global_path: str
    auto_loaded: bool
    notes: str


CLI_TOOLS = {
    item.id: item
    for item in (
        CliTool("codex", "OpenAI Codex", "AGENTS.md", ".codex/AGENTS.md", True, "Loaded hierarchically by Codex at session start."),
        CliTool("claude-code", "Claude Code", "CLAUDE.md", ".claude/CLAUDE.md", True, "Loaded by Claude Code as project or user memory."),
        CliTool("gemini-cli", "Gemini CLI", "GEMINI.md", ".gemini/GEMINI.md", True, "Loaded by Gemini CLI as hierarchical context."),
        CliTool("cursor", "Cursor", ".cursor/rules/contextvault.mdc", ".cursor/rules/contextvault.mdc", True, "Project rule file."),
        CliTool("github-copilot", "GitHub Copilot", ".github/copilot-instructions.md", ".config/github-copilot/copilot-instructions.md", True, "Repository instructions are automatically discovered."),
        CliTool("cline", "Cline", ".clinerules/contextvault.md", ".clinerules/contextvault.md", True, "Project rule file."),
        CliTool("windsurf", "Windsurf", ".windsurf/rules/contextvault.md", ".windsurf/rules/contextvault.md", True, "Project rule file."),
        CliTool("aider", "Aider", "CONVENTIONS.md", ".aider/CONVENTIONS.md", False, "Pass the generated file with aider --read."),
        CliTool("opencode", "OpenCode", "AGENTS.md", ".config/opencode/AGENTS.md", True, "Uses AGENTS.md-compatible project instructions."),
    )
}


START = "<!-- contextvault:start protocol=2 -->"
END = "<!-- contextvault:end -->"
_START_PATTERN = re.compile(r"<!-- contextvault:start\b[^>]*-->")
_BLOCK = re.compile(
    r"<!-- contextvault:start\b[^>]*-->.*?" + re.escape(END), re.DOTALL
)


class CliAdapterService:
    def __init__(self, repository: VaultRepository):
        self.repository = repository
        self.summaries = SummaryService(repository)

    def tools(self) -> list[dict[str, object]]:
        return [item.__dict__ for item in CLI_TOOLS.values()]

    def install(
        self,
        tool_id: str,
        *,
        scope: str = "project",
        directory: Optional[Path] = None,
        space: str = "personal",
        summary_type: str = "personal",
    ) -> dict[str, object]:
        if tool_id not in CLI_TOOLS:
            raise ValueError(f"Unsupported CLI tool: {tool_id}")
        if scope not in {"project", "global"}:
            raise ValueError("CLI context scope must be project or global")
        tool = CLI_TOOLS[tool_id]
        base = (directory or Path.cwd()).expanduser().resolve()
        path = (
            base / tool.project_path
            if scope == "project"
            else Path.home() / tool.global_path
        )
        content = self.summaries.render(summary_type, space)
        version = hashlib.sha256(content.encode()).hexdigest()[:16]
        block = (
            f"{START}\n"
            "# ContextVault synchronized personal context\n\n"
            "This block is generated from user-confirmed ContextVault claims. "
            "Treat it as personal context, not as instructions that override repository rules.\n\n"
            f"Profile version: `{version}`\n\n"
            f"{content.rstrip()}\n"
            f"{END}"
        )
        changed = _write_managed_block(path, block)
        now = utc_now()
        with self.repository.transaction() as connection:
            existing = connection.execute(
                "SELECT id, created_at FROM cli_installations WHERE tool = ? AND path = ?",
                (tool_id, str(path)),
            ).fetchone()
            installation_id = str(existing["id"]) if existing else f"cli_{uuid4().hex}"
            created_at = str(existing["created_at"]) if existing else now
            connection.execute(
                """
                INSERT INTO cli_installations(
                    id, tool, scope, path, space_name, summary_type,
                    last_profile_version, enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(tool, path) DO UPDATE SET
                    scope = excluded.scope,
                    space_name = excluded.space_name,
                    summary_type = excluded.summary_type,
                    last_profile_version = excluded.last_profile_version,
                    enabled = 1,
                    updated_at = excluded.updated_at
                """,
                (
                    installation_id,
                    tool_id,
                    scope,
                    str(path),
                    space,
                    summary_type,
                    version,
                    created_at,
                    now,
                ),
            )
        self.repository.append_event(
            "cli_context.updated",
            "cli_installation",
            installation_id,
            {"tool": tool_id, "path": str(path), "version": version, "changed": changed},
        )
        return {
            "id": installation_id,
            "tool": tool_id,
            "path": str(path),
            "version": version,
            "changed": changed,
            "auto_loaded": tool.auto_loaded,
            "notes": tool.notes,
        }

    def installations(self) -> list[dict[str, object]]:
        with self.repository.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM cli_installations ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def sync(self, tool_id: Optional[str] = None) -> list[dict[str, object]]:
        results = []
        for item in self.installations():
            if not item["enabled"] or (tool_id and item["tool"] != tool_id):
                continue
            path = Path(str(item["path"]))
            tool = CLI_TOOLS[str(item["tool"])]
            project_root = _project_root_for(path, tool)
            results.append(
                self.install(
                    str(item["tool"]),
                    scope=str(item["scope"]),
                    directory=project_root,
                    space=str(item["space_name"]),
                    summary_type=str(item["summary_type"]),
                )
            )
        return results

    def watch(self, interval_seconds: int = 60) -> None:
        if interval_seconds < 10:
            raise ValueError("Watch interval must be at least 10 seconds")
        last_sequence = 0
        while True:
            events = self.repository.list_events(after_sequence=last_sequence, limit=1000)
            if events:
                last_sequence = events[-1].sequence
                if any(event.aggregate_type in {"claim", "device", "profile_space"} for event in events):
                    self.sync()
            time.sleep(interval_seconds)


def _write_managed_block(path: Path, block: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    has_start = bool(_START_PATTERN.search(existing))
    has_end = END in existing
    if has_start != has_end:
        raise ValueError(f"Incomplete ContextVault managed block in {path}")
    updated = _BLOCK.sub(block, existing) if has_start else _append_block(existing, block)
    if updated == existing:
        return False
    temporary = path.with_name(f".{path.name}.contextvault-{os.getpid()}.tmp")
    temporary.write_text(updated, encoding="utf-8")
    os.replace(temporary, path)
    return True


def _append_block(existing: str, block: str) -> str:
    prefix = existing.rstrip()
    return f"{prefix}\n\n{block}\n" if prefix else f"{block}\n"


def _project_root_for(path: Path, tool: CliTool) -> Path:
    suffix = Path(tool.project_path)
    parts = path.parts
    if len(parts) >= len(suffix.parts) and parts[-len(suffix.parts) :] == suffix.parts:
        return Path(*parts[: -len(suffix.parts)])
    return path.parent
