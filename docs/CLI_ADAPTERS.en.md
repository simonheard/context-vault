# Coding CLI adapters

[中文](CLI_ADAPTERS.md)

## Supported tools

- OpenAI Codex: project `AGENTS.md`, global `~/.codex/AGENTS.md`;
- Claude Code: project `CLAUDE.md`, global `~/.claude/CLAUDE.md`;
- Gemini CLI: project `GEMINI.md`, global `~/.gemini/GEMINI.md`;
- Cursor, GitHub Copilot, Cline, Windsurf, Aider, and OpenCode.

ContextVault writes an HTML-comment-delimited managed block. Updates replace only that block and preserve existing project rules. Older protocol-1 blocks are upgraded in place to protocol 2 instead of duplicated. Project scope is the default; user-directory files are touched only with explicit `--scope global`.

```bash
contextvault cli list
contextvault cli install codex --scope project --directory .
contextvault cli install claude-code --scope global
contextvault cli install gemini-cli --summary-type work
contextvault cli status
contextvault cli sync
contextvault cli watch --interval 60
```

`watch` follows the local event sequence and refreshes installed context files after claim, device, or profile-space changes. Codex, Claude Code, and Gemini CLI reload their native context files according to their own new-session behavior. Aider is not guaranteed to auto-discover its generated file; use `aider --read CONVENTIONS.md`.

The generated block explicitly says that personal profile data is user context, not a higher-priority instruction capable of overriding repository rules or system security policy.
