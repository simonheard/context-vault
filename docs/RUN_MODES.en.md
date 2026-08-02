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
python -m pip install context_vault-0.11.0-py3-none-any.whl
contextvault-cli init
contextvault-cli import chatgpt-export.zip
contextvault-cli claims confirm-all
contextvault-cli summary --type personal
contextvault-cli cli install codex --scope project
```

The CLI uses local SQLite and supports official exports, review, devices, summaries, routes, and coding-agent file adapters. Web-service collaboration is activated only when the user invokes `ui`, `daemon`, `captures`, or `extension` commands.

## Optional advanced connected mode

The extension can switch to “connect local service” when the user wants complete SQLite auditing, multi-account routes, server policy, local models, or cross-client events. It does not copy the standalone vault automatically. Move data explicitly with `import --format browser-vault` or `profile export-browser` so two profile copies never overwrite each other without the user's knowledge.
