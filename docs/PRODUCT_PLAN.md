# Product plan

## Positioning

`aimem` is a user-owned context layer between AI providers. It helps people
move useful history, preferences, decisions, project state, and artifacts
without treating every raw conversation as permanent truth.

Primary promise:

> Your AI context belongs to you, not to one AI provider.

The initial target user is a developer who uses multiple AI tools and needs
project context to survive provider changes. This segment has clear pain,
structured data, strong CLI adoption, and a plausible path to paid features.

## Problems to solve

1. Official export formats differ and change over time.
2. Raw chat history is noisy, stale, contradictory, and expensive as context.
3. Users cannot easily audit what one AI learned from another.
4. Browser-only automation is fragile and may create platform-account risk.
5. Centralized plaintext storage creates unacceptable privacy exposure.

## MVP scope

### In scope

- Import ChatGPT, Claude, and Gemini official exports.
- Normalize conversations, messages, attachments, and source metadata.
- Store locally in SQLite with FTS5 full-text search.
- Detect duplicate messages and conversations.
- Extract memory candidates with explicit lifecycle states.
- Review, confirm, edit, expire, or delete memory candidates.
- Detect common secrets and sensitive fields before export.
- Export portable Markdown and JSON context packages.
- Generate provider-oriented packages without claiming native restoration.

### Out of scope

- Unattended web scraping or automated message sending.
- Server-side plaintext AI inference.
- Real-time two-way synchronization.
- Knowledge graphs or a mandatory vector database.
- Passwords, API keys, session cookies, or authentication-token storage.
- Enterprise administration in the first release.

## Milestones

### M0 — Foundation (current)

- Product boundaries and threat model.
- Repository, CI-ready package layout, SQLite schema, CLI bootstrap.
- Acceptance: a user can initialize a local vault and inspect its status.

### M1 — Data converter

- Import adapter interface and fixture-driven test suite.
- ChatGPT export adapter first; Claude and Gemini next.
- Normalized JSON/Markdown output and deterministic deduplication.
- Acceptance: supported fixtures round-trip without losing message ordering,
  timestamps, roles, or source references.

### M2 — Local knowledge base

- FTS5 search, filters, project tags, attachment metadata, and timeline.
- Memory candidate extraction plus manual confirmation workflow.
- Secret/sensitivity scanner and export preview.
- Acceptance: a user can find a prior decision and create a reviewed project
  context pack without network access.

### M3 — Browser extension

- Explicit “save conversation” and “save selected messages” actions.
- Search local history and inject a reviewed context pack.
- Independent adapters and health checks for each supported website.
- Acceptance: failures disable only the affected adapter and never capture data
  silently.

### M4 — Encrypted sync

- Multi-device encrypted blob sync, version history, and conflict handling.
- XChaCha20-Poly1305 vault encryption and Argon2id key derivation.
- Server cannot decrypt vault content; recovery behavior is documented.
- Acceptance: a fresh device can restore and verify a vault while the server
  only observes ciphertext and limited operational metadata.

## Six-week validation plan

### Weeks 1–2

- Implement normalized schema and ChatGPT fixture importer.
- Interview 8–12 multi-AI developers.
- Measure: repeated migration/search pain and willingness to run a local CLI.

### Weeks 3–4

- Add Claude/Gemini fixtures, FTS5 search, and Markdown context packs.
- Dogfood on at least three real exports with private fixtures kept outside Git.
- Measure: import success, duplicate rate, time-to-find, and export usefulness.

### Weeks 5–6

- Add memory review and redaction preview.
- Release a private alpha to 10–20 users.
- Measure: weekly retained users, reviewed exports, false-memory corrections,
  and which job dominates—backup, migration, search, or context injection.

## MVP success criteria

- At least 90% of alpha exports import without manual repair.
- A known item can be found in under 30 seconds.
- No content leaves the machine without a preview and explicit action.
- Every exported memory links back to its source.
- At least 5 alpha users repeat the workflow in a second week.

## Key risks and mitigations

| Risk | Mitigation |
|---|---|
| Vendor format drift | Versioned adapters, fixtures, graceful unsupported reports |
| Incorrect extracted memories | Candidate-by-default, provenance, confidence, user confirmation |
| Secret leakage | Local scanning, sensitivity labels, export preview, denylist rules |
| Browser DOM changes | Isolated adapters, health checks, user-triggered capture only |
| Platform terms/account risk | Prefer official exports; no cookie reuse or unattended automation |
| Scope explosion | Ship CLI converter and search before extension or VPS |

## Early decisions

- Python for CLI and local service; TypeScript for the future extension.
- SQLite and FTS5 before embeddings or a vector database.
- Provider adapters at system boundaries; normalized records internally.
- Browser extension is an incremental capture client, not the source of truth.
- VPS is a blind encrypted sync service, not the AI-processing core.

