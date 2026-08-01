# Architecture

[中文](ARCHITECTURE.md)

## System shape

```text
Official exports / manual files
              |
              v
        Import adapters
              |
              v
  Normalize, validate, dedupe
              |
              v
  Local SQLite vault + FTS5
         |                 |
         v                 v
  Review/redaction    Export adapters
                            |
               Markdown / JSON / provider packs

Future browser extension ---> local service
Future encrypted sync <-----> ciphertext-only VPS
```

Official exports and manual files are the primary first-stage inputs. Provider
adapters parse them, while the core works only with normalized records. Only
reviewed data reaches export adapters. Neither the extension nor the VPS is the
system of record.

## Package direction

```text
CLI -> application services -> domain model
                         |-> import adapters
                         |-> export adapters
                         |-> vault repository
```

Vendor schemas must not leak into the domain model: import adapters produce
normalized records and export adapters consume reviewed records.

## Core objects

- `Conversation`: source identity, title, timestamps, participants, and scope.
- `Message`: stable source reference, role, content parts, ordering, and timestamps.
- `Artifact`: local content-addressed artifact metadata; secrets are prohibited.
- `Memory`: profile, preference, project, decision, fact, task, or summary.
- `Export`: immutable manifest of what the user deliberately sent and where.

Every memory carries provenance, confidence, validity, sensitivity, scope, and
lifecycle state.

```text
candidate -> confirmed -> expired
     |           |
     v           v
  deleted     conflicted
```

`inferred` describes an extraction method; it is not permission to export.

## Local vault

The current schema contains metadata and memory tables plus an FTS5 index. M1
will add conversation, message, and artifact migrations with the import
adapters. Schema changes must be versioned and forward-only, with backups before
destructive changes.

```text
.contextvault/
  vault.sqlite
  artifacts/<sha256-prefix>/<sha256>
  exports/<export-id>/manifest.json
  config.toml
```

## Trust boundaries

- Provider exports are untrusted: reject path traversal, decompression bombs,
  malformed encodings, oversized files, and executable attachments.
- The vault may be highly sensitive; restrictive permissions and encryption at
  rest are required before broad release.
- LLM extraction is untrusted: validate its schema and confirm high-risk facts.
- The extension sends only reviewed data to provider pages.
- The future server receives only ciphertext and minimal sync metadata.

## Adapter contracts

Import adapters should expose detection, validation, iteration, and format
version. Export adapters should declare target capabilities so the CLI can
explain whether a provider accepts full history, a context document, or another
package type.

## Encryption direction

For M4, derive a wrapping key with Argon2id, generate a random key per vault,
and encrypt objects with XChaCha20-Poly1305. The server must never receive the
user secret or plaintext vault key. The protocol requires an independent
security review before implementation.

