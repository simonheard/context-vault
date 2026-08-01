# Attachment References and Cross-AI Handling

[中文](ATTACHMENTS.md)

## Architecture decision

The ContextVault database stores text, structured profile data, attachment
references, sync policies, and audit records only. Original files remain hosted
by ChatGPT, Gemini, Claude, or another AI provider. ContextVault does not provide
default R2, S3, or other object storage and is not the long-term backup for
original attachments.

## AttachmentRef

A remote URL is insufficient because it may be temporary, session-dependent,
or bound to one account. Attachment identity combines provider, source account,
and provider file ID.

```text
attachment_refs
- id
- vault_id
- provider_account_id
- provider
- provider_file_id
- conversation_id
- message_id
- remote_url              # ephemeral cache, not permanent identity
- filename
- mime_type
- size_bytes
- sha256                  # deduplication when available
- description
- extracted_text          # stored only with user permission
- sensitivity
- status                  # active / missing / expired / denied
- last_verified_at
- created_at
```

`provider_account_id` is a required boundary. Personal and work accounts on the
same provider never share attachment access implicitly.

## Three synchronization modes

### Reference only

The target receives filename, type, provenance, description, and status, but no
file content.

```text
Attachment: 2025 Tax Return.pdf
Source: Personal ChatGPT
Type: PDF
Description: 2025 tax filing material
Status: Still hosted by ChatGPT and not sent to this target
```

This is appropriate when the profile only needs to record that a file exists.

### Extracted text

With permission, a local agent reads the file, extracts text, scans and redacts
secrets, and stores only approved text or a summary. The original file is not
retained.

```text
source attachment -> temporary local read -> text extraction -> scan and preview
                  -> extracted_text -> target profile package
```

Extracted text inherits the attachment's sensitivity and account/space boundary.

### User-triggered transient transfer

On an explicit user action, the extension or local agent reads the file from the
source account and uploads it to the target account. Bytes exist only in memory
or a restricted temporary directory and are deleted after success or failure.
The database stores source and target references, result, and receipt only.

## Reference states

- `active`: accessible from the current account and device;
- `reauth_required`: the source account needs sign-in;
- `expired`: the cached URL expired, while the provider file ID may remain valid;
- `missing`: the source file was deleted or cannot be found;
- `permission_denied`: the current account lacks access;
- `device_unavailable`: another device or browser session is required;
- `copied`: the target provider now has its own reference.

Validate references periodically or immediately before use, without repeatedly
downloading files merely to check status.

## Multi-device limitation

A new device may know an attachment exists without being able to read it because
it is not signed in to the same provider account. The UI distinguishes reference
availability from current-device access capability.

## Privacy rules

- References may themselves be sensitive through filenames, conversation titles, or account labels.
- Show file, target, and sensitivity risk before extracting text.
- Reject extracted-text storage and automatic transfer when secret detection triggers.
- Never write transient bytes to long-term caches, logs, or crash reports.
- Use random temporary names, restrictive permissions, and cleanup on success, failure, and process exit.
- Receipts identify the attachment sent without duplicating its content.

## Failure and recovery

When an attachment becomes unavailable, retain its reference and provenance so
the user can:

- reauthenticate in the correct account;
- resolve it from a device that still has access;
- select a replacement manually;
- synchronize only the existing description or extracted text;
- mark the reference permanently lost.

## Optional external storage later

Users who need independent backup may connect their own S3, WebDAV, Google
Drive, or another storage provider. This remains an optional connector with its
own authorization and encryption policy, never a hidden default file store.

