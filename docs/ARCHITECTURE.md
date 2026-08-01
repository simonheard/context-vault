# Architecture

## System shape

```text
Official exports / manual files
              |
              v
      Import adapters (CLI)
              |
              v
  Normalization + validation + dedupe
              |
              v
  Local SQLite vault + FTS5 + artifacts
         |                     |
         v                     v
 Review/redaction        Export adapters
                               |
                     Markdown / JSON / provider packs

Future browser extension ----> local service
Future encrypted sync <------> ciphertext-only VPS
```

## Package direction

```text
cli -> application services -> domain model
                         |-> import adapters
                         |-> export adapters
                         |-> vault repository
```

Vendor-specific schemas must not leak into the domain model. Import adapters
produce normalized records; export adapters consume reviewed normalized data.

## Core objects

- `Conversation`: source identity, title, timestamps, participants, scope.
- `Message`: stable source reference, role, content parts, ordering, timestamps.
- `Artifact`: local content-addressed file metadata; secret material prohibited.
- `Memory`: profile, preference, project, decision, fact, task, or summary.
- `Export`: immutable manifest of what was deliberately sent and where.

Every memory includes provenance, confidence, validity period, sensitivity,
scope, and one of these states:

```text
candidate -> confirmed -> expired
     |           |
     v           v
  deleted     conflicted
```

`inferred` is recorded as an extraction method, not permission to export.

## Local vault

The bootstrap schema creates metadata and memory tables plus an FTS5 index.
Conversation/message/artifact migrations will be added alongside M1 adapters.
Schema changes must be versioned and forward-only, with backups before a
destructive migration.

Suggested production layout:

```text
.aimem/
  vault.sqlite
  artifacts/<sha256-prefix>/<sha256>
  exports/<export-id>/manifest.json
  config.toml
```

## Trust boundaries

- Provider exports are untrusted input: reject path traversal, decompression
  bombs, malformed encodings, oversized members, and executable attachments.
- The local vault may contain highly sensitive data; restrictive permissions
  and encrypted-at-rest support are required before broad release.
- LLM extraction output is untrusted: validate schema and require confirmation
  for high-risk facts.
- The browser extension sends only user-reviewed data to a provider page.
- The future server receives encrypted objects and minimal sync metadata only.

## Adapter contracts

Import adapters should expose detection, validation, iteration, and a format
version. Export adapters should declare capability limits so the CLI can explain
whether a target accepts full history, a context document, or another package.

## Encryption direction

For M4, derive a wrapping key from the user's secret with Argon2id, generate a
random key per vault, and encrypt objects with XChaCha20-Poly1305. The server
must never receive the user secret or plaintext vault key. The exact protocol
requires a dedicated security review before implementation.

