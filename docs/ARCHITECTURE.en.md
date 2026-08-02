# Architecture

[中文](ARCHITECTURE.md)

## System shape

```text
┌──────────────────── Sources ─────────────────────┐
│ AI exports │ browser extension │ device agent │ manual │
└──────────────────────┬──────────────────────────┘
                       v
┌──────────── Collection and normalization ────────┐
│ source adapters │ parsing │ dedupe │ secret scan │
└──────────────────────┬──────────────────────────┘
                       v
┌──────────── Understanding and merge ─────────────┐
│ claim extraction │ time │ conflicts │ review     │
└──────────────────────┬──────────────────────────┘
                       v
┌────────────── Canonical personal profile ────────┐
│ user │ education │ work │ preference │ project  │
│ people │ devices │ environment │ goals │ timeline│
└───────────────┬──────────────────────┬───────────┘
                v                      v
        summary generator       sync policy engine
                \                      /
                 v                    v
           Gemini │ Claude │ ChatGPT │ other targets
```

## Truth, evidence, and synchronized copies

The system separates:

1. **Evidence:** original messages, device scans, and manual input.
2. **Canonical profile:** merged, confirmed, time-aware personal information and the source of truth.
3. **Synchronized copy:** a target-specific summary or field subset.

An LLM summary is not truth by itself, and a copy already sent to Gemini must
not overwrite the canonical profile.

## Core data objects

### Entity

The user, a school, company, person, project, device, or place. Devices are
entities and can have aliases, relationships, timelines, and independent claims.

### Claim

A single verifiable statement about an entity, including:

- `entity_id`, `attribute`, and structured `value_json`;
- source platform, conversation, message, or scan ID;
- `confidence`, `status`, and `sensitivity`;
- `valid_from`, `valid_until`, and `observed_at`;
- creation, update, and confirmation metadata.

```text
candidate -> confirmed -> superseded -> expired
     |            |             |
     v            v             v
  rejected     conflicted     deleted
```

### Device

A structured extension of a device entity with type, stable fingerprint,
last-seen time, and approved configuration. Serial numbers, full IP addresses,
usernames, and paths require sensitivity policies.

### SyncTarget

A synchronization configuration for one provider account without login
credentials. It references `ProviderAccount` and stores allowed categories,
sensitivity ceiling, summary budget, sync method, and last version.

### ProviderAccount

A local reference containing provider, local label, optional irreversible
account-identifier hash, and status. Evidence, targets, consent, and receipts
always bind to a specific account.

### ProfileSpace and SyncRoute

`ProfileSpace` isolates personal, work, client, and anonymous data. `SyncRoute`
defines source account, space, and destination account. A new account has no
route by default, and work spaces cannot flow to personal accounts by default.

### SyncReceipt

Records which claims a sync sent, which summary version it used, whether it
succeeded, and how it can later be corrected or revoked.

### ConsentReceipt

Records the risk-notice version, allowed sensitive categories, sync mode,
acknowledgement time, and revocation time for one target. It is an audit record
of informed consent, contains no authentication credentials, and cannot prove
that a provider deleted previously received data.

## Extraction pipeline

```text
raw message
 -> cleanup and role detection
 -> retrieve user-related passages
 -> extract structured candidates
 -> validate schema
 -> resolve and deduplicate entities
 -> compare with existing claims
 -> add / confirm / conflict / expire old value
 -> review queue or policy-based confirmation
```

LLMs propose candidates from natural language. Deterministic code handles schema
validation, time calculations, secret rejection, deduplication, and policy.
Identity, medical, legal, financial, and relationship inferences are never
auto-confirmed.

## Device agent

Device collection is layered:

- **Base:** device type, model, CPU, memory, OS, and version.
- **Development:** shell, editor, language runtimes, package managers, containers, and Git.
- **Software:** only applications allowed by the user.
- **Configuration:** allowlisted keys only; environment values and authentication files are excluded by default.
- **Projects:** repository names, stacks, and path aliases; source code is not uploaded by default.

The agent produces a local diff first. Policy decides which changes enter the
canonical profile and which may be synchronized to an AI.

## Summary generation

A summary is a rebuildable view, not the primary storage format. The generator
accepts a target, use case, allowed categories, sensitivity ceiling, character
or token budget, and previous sync version. It emits both complete and change
summaries plus a machine-readable manifest of included claim IDs.

Before output, the generator enforces policy: `block` fields are removed, `ask`
fields enter confirmation, and `allow` fields still pass secret scanning and
provider constraints.

## Sync methods

In order of stability:

1. Official API or import format.
2. User-triggered file import.
3. One-click copy of structured profile data.
4. Browser capture, dedicated-chat creation, or injection on a page where the user is already signed in.
5. Never store cookies on a server to impersonate the user.

## Attachment handling

ContextVault does not retain attachment binaries. `AttachmentRef` binds a source
`ProviderAccount`, provider file ID, conversation, and message, plus filename,
type, size, optional hash, description, access status, and optional extracted
text. A remote URL is an ephemeral locator rather than permanent identity.

Cross-provider handling supports reference-only sync, user-approved extracted
text, and user-triggered transient transfer. Transient files exist only in
memory or a temporary directory and are deleted after transfer. The database
continues to store only text, references, and receipts.

## Local storage

```text
.contextvault/
  vault.sqlite
  sources/<source-id>/manifest.json
  summaries/<target>/<version>.md
  sync-receipts/<target>/<version>.json
  config.toml
```

SQLite stores entities, claims, devices, targets, versions, search,
relationships, attachment references, and optional extracted text. Original
attachments remain hosted by AI providers. A future vector index is a
rebuildable cache rather than the source of truth.

## Encryption and server

The default is fully local. Multi-device sync uses a random vault key and
XChaCha20-Poly1305; Argon2id derives a wrapping key from the user secret. The
server stores encrypted text events, versions, and minimal routing metadata
only. It stores no original attachment files.

## Suggested modules

```text
contextvault/
  domain/        # entity, claim, device, policy, receipt
  importers/     # chatgpt, claude, gemini, files
  extractors/    # profile, timeline, device references
  merge/         # identity resolution, conflict, validity
  summaries/     # personal, work, project, devices
  targets/       # gemini, claude, chatgpt
  device_agent/  # platform scanners and allowlists
  attachments/   # provider references, extraction, transient transfer
  storage/       # sqlite, text events, migrations
  cli/           # commands and review UI
```
