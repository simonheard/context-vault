# Independent run modes

[中文](RUN_MODES.md)

ContextVault ships two separately installable and independently runnable surfaces. Neither is a required dependency of the other, and they never merge profile data silently.

## Standalone browser extension

Install `contextvault-extension.zip` and choose “use the extension directly.” Python, the CLI, Codex, and a local HTTP service are not required.

- Up to 5,000 text claims, configuration, and 200 receipts live in the current Chrome Profile's `chrome.storage.local`.
- It can pull the current chat, create a knowledge-probe chat on a blank page, review candidates, build a profile package, and fill or automatically send it.
- Pending candidates are not sent, `secret` data is rejected, and `sensitive` data is excluded from unattended sync by default.
- Three page failures trip a circuit breaker; a possibly sent operation pauses and is never retried automatically.
- Each Chrome Profile is an account boundary. Use separate Chrome Profiles for multiple accounts on the same provider.
- Export JSON before uninstalling the extension or clearing its data. Chrome extension storage is not an end-to-end encrypted vault; at-rest protection relies on OS disk encryption.

The extension management page supports confirm, reject, manual add, import, and export. Its schema-1 JSON backup can move into the CLI:

```bash
contextvault-cli import contextvault-browser-2026-08-02.json --format browser-vault
contextvault-cli profile export-browser contextvault-browser.json
```

## Standalone CLI

Install `context_vault-*.whl` and use `contextvault-cli`. The browser extension, Chrome, and web management UI are not required.

```bash
python -m pip install context_vault-0.12.0-py3-none-any.whl
contextvault-cli init
contextvault-cli import chatgpt-export.zip
contextvault-cli claims confirm-all
contextvault-cli summary --type personal
contextvault-cli cli install codex --scope project
```

The CLI uses local SQLite and supports official exports, review, devices, summaries, routes, and coding-agent file adapters. Web-service collaboration is activated only when the user invokes `ui`, `daemon`, `captures`, or `extension` commands.

## Optional advanced connected mode

The two surfaces can work together when the user wants complete SQLite auditing, multi-account routes, server policy, local models, or cross-client events:

```bash
contextvault link
```

The command displays an eight-digit code and starts the loopback service. Enter the code in the extension and select “merge and connect.” The code expires after ten minutes, works once, and is invalidated after five failed attempts. The long token remains only as an advanced fallback.

On link, the extension deduplicates standalone claims by attribute and value, preserves pending/confirmed state in SQLite, creates a safe default account and route for the current provider with automation off and sensitive data blocked, and switches to connected mode. On a new provider, one “create default account and route” button performs the same safe setup. SQLite then becomes the only source of truth; the extension handles browser capture and push without continuing to mutate a second standalone copy. “Disconnect and use standalone” first downloads a fresh SQLite snapshot, revokes the current client token, and only then returns to standalone mode. A failed transition deletes neither copy.

JSON `import` and `export-browser` remain available for offline migration and backup.
