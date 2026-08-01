# Product Plan

[中文](PRODUCT_PLAN.md)

## Positioning

ContextVault is a user-owned context layer between AI providers. It moves useful
history, preferences, decisions, project state, and artifacts without treating
every raw conversation as permanent truth.

The initial target is developers who use multiple AI tools: their pain is clear,
their data is structured, and they are comfortable with a CLI.

## Problems to solve

1. Official export formats differ and change.
2. Raw history is noisy, stale, contradictory, and expensive as context.
3. Users cannot easily audit what one AI learned from another.
4. Browser-only automation is fragile and may create account risk.
5. Centralized plaintext storage creates unacceptable privacy exposure.

## MVP scope

### In scope

- Import official exports from ChatGPT, Claude, and Gemini.
- Normalize conversations, messages, attachments, and source metadata.
- Use SQLite and FTS5 for local storage and full-text search.
- Deterministically deduplicate messages and conversations.
- Extract reviewable memory candidates that can be confirmed, edited, expired, or deleted.
- Detect common secrets and sensitive fields before export.
- Export Markdown, JSON, and provider-oriented context packages.

### Out of scope

- Unattended scraping or automated bulk messaging.
- Server-side inference over plaintext data.
- Real-time bidirectional sync in the first release.
- A mandatory knowledge graph or vector database.
- Storing passwords, API keys, cookies, or authentication tokens.

## Milestones

### M0 — Foundation (current)

- Define product boundaries and the threat model.
- Establish the repository, CLI, SQLite schema, and testable package structure.
- Acceptance: initialize a local vault and inspect its status.

### M1 — Data converter

- Define import adapters and fixture tests.
- Support ChatGPT, Claude, then Gemini.
- Produce normalized JSON/Markdown with deterministic deduplication.
- Acceptance: preserve ordering, timestamps, roles, and source references.

### M2 — Local knowledge base

- Add search, filters, project tags, attachment metadata, and timeline views.
- Add memory review, sensitivity scanning, and export preview.
- Acceptance: find a prior decision and build a reviewed context pack fully offline.

### M3 — Browser extension

- Provide only user-triggered save, search, and injection actions.
- Isolate platform adapters and add health checks.
- Acceptance: one broken adapter does not affect others and capture is never silent.

### M4 — Encrypted sync

- Add encrypted multi-device sync, version history, and conflict handling.
- Use Argon2id and XChaCha20-Poly1305 for vault encryption.
- Acceptance: a new device restores and verifies a vault while the server sees only ciphertext and minimal metadata.

## Six-week validation plan

### Weeks 1–2

- Implement the normalized model and ChatGPT fixture importer.
- Interview 8–12 multi-AI developers.
- Measure repeated pain and willingness to run a local CLI.

### Weeks 3–4

- Add Claude and Gemini fixtures, FTS5 search, and Markdown context packs.
- Dogfood at least three real exports; keep private fixtures outside Git.
- Measure import success, duplicate rate, time-to-find, and export usefulness.

### Weeks 5–6

- Add memory review and redaction preview.
- Release a private alpha to 10–20 users.
- Determine whether the dominant job is backup, migration, search, or context injection.

## Success criteria

- At least 90% of alpha exports import without manual repair.
- Find a known item within 30 seconds.
- Nothing leaves the machine without preview and explicit action.
- Every exported memory links to its source.
- At least five alpha users repeat the workflow in week two.

## Key risks

| Risk | Mitigation |
|---|---|
| Provider format drift | Versioned adapters, fixtures, and clear errors |
| Incorrect memories | Candidate-by-default, provenance, confidence, and confirmation |
| Secret leakage | Local scanning, sensitivity labels, and export preview |
| Browser DOM changes | Isolated adapters, health checks, and user-triggered capture |
| Scope growth | Ship the CLI, converter, and search first |

## Early technical decisions

- Python for the CLI and local service; TypeScript for the future extension.
- SQLite and FTS5 before embeddings or a vector database.
- Keep provider differences in boundary adapters.
- The browser extension is an incremental client, not the source of truth.
- The VPS is a blind sync service, not the inference core.

