# Implementation status

[中文](IMPLEMENTATION_STATUS.md)

## v0.7 local closed loop

The following capabilities now run through the CLI or local management UI:

- parse an official ChatGPT ZIP or `conversations.json` export;
- retain source account, conversation, message, and content hashes with idempotent imports;
- detect common passwords, private keys, API keys, cookies, and tokens before evidence is stored, replacing matching messages with a redaction marker;
- extract profile candidates with deterministic Chinese and English rules that never execute instructions found in conversations;
- confirm, bulk-confirm, reject, conflict, delete, full-text search, and trace candidate claims;
- render canonical Markdown/JSON profiles plus work, project, device, and recent-change summaries;
- manage multiple AI accounts, profile spaces, account disconnection/revocation, and source-space-target routes;
- scan local model, OS, CPU, memory, and development-tool versions without reading environment-variable values or credential files;
- enforce a global sensitive-sync gate, route-level category/sensitivity/budget policy, and informed-consent receipts;
- produce sync previews, blocked-field explanations, per-run confirmation, incremental diffs, Markdown packages, and sync receipts;
- include provider attachment references or approved extracted text while keeping attachment binaries out of the database;
- maintain an append-only event log, multi-device cursors, profile-health metrics, and schema migrations.

## Capabilities requiring an external platform or deployed infrastructure

The following cannot be completed by a local repository without target-platform authorization, a logged-in browser session, or a sync server:

- ChatGPT, Gemini, and Claude browser extensions and page-writing adapters;
- official provider APIs, file upload, verified remote deletion, and post-sync question validation;
- interactive attachment download and transfer between logged-in provider accounts;
- a multi-device end-to-end encrypted server, key recovery, and device revocation;
- optional local LLM and calendar, contacts, repository, or smart-home connectors.

The local implementation supplies route, manifest, receipt, event-cursor, and provider-adapter boundaries for those integrations. Each adapter must still follow the provider's APIs, account policy, and the user's authorization; server-side cookie-based login simulation remains prohibited.

## Runnable commands

```bash
contextvault import chatgpt-export.zip --account <account-id>
contextvault claims list
contextvault claims confirm-all
contextvault profile health
contextvault summary --type work
contextvault devices scan
contextvault routes add --from <source> --space personal --to <target>
contextvault routes preview <route-id>
contextvault privacy enable-sensitive
contextvault privacy consent <route-id> --categories health,finance --mode ask
contextvault sync run <route-id> --output gemini-profile.md
contextvault sync receipts
contextvault ui
```
