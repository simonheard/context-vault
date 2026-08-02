# User-session browser extension

[中文](BROWSER_EXTENSION.md)

## How it works

The extension uses supported AI pages where the user is already signed in through Chrome. ContextVault never reads, stores, or uploads passwords, cookies, OAuth tokens, or sessions. The extension only:

1. identifies the supported provider and checks that a composer is available;
2. reads the configured route preview from `127.0.0.1:8787`;
3. pulls the user-authorized current conversation or creates a knowledge-probe chat on a blank page;
4. displays final text, policy-blocked fields, and sensitive fields requiring per-run approval;
5. in semi-automatic mode, asks the user to confirm the target account and leaves sending to the user;
6. in full automation, creates or reuses a route-specific chat and clicks only an explicitly recognized enabled Send control;
7. uses durable receipts, page markers, and circuit breakers to recover interruptions without duplicate sends.

If a provider changes its page structure and the composer adapter stops working, the user can still use the extension's Copy button or generate a Markdown file through the CLI.

## Installation

1. Start the local service:

   ```bash
   contextvault ui
   ```

2. Open `chrome://extensions` and enable Developer mode.
3. Select “Load unpacked” and choose the repository's `extension/` directory.

   Alternatively, run `python3 scripts/package_extension.py` to create
   `dist/contextvault-extension.zip`. Every GitHub Actions build on `main` also publishes the same artifact.
4. Get the pairing token:

   ```bash
   contextvault extension token
   ```

   It is also available on the management UI's Privacy page.

5. Paste the token into the extension and save. It authorizes only local ContextVault API access.
6. Sign in normally to the target AI, open a conversation, and select the extension icon.

Run `contextvault extension rotate-token` when an already paired extension is no longer trusted. Every old token becomes invalid immediately, and retained extensions must pair again with the new token.

## Preparation

Create at least one target account and route:

```bash
contextvault accounts add --platform gemini --label "Personal Gemini"
contextvault routes add --space personal --to <gemini-account-id>
```

The extension shows only enabled routes whose target provider matches the current page. Semi-automatic mode requires account confirmation each time. Full automation cannot reliably inspect the provider account identity, so it requires a risk acknowledgement; using one target account per Chrome Profile is recommended.

## Security boundary

- the API remains loopback-only by default;
- extension requests require a random vault pairing token;
- the token lives in Chrome extension local storage and is not a provider credential;
- the extension never reads cookies, scrapes conversation history, or simulates server-side login;
- full automation is off by default and requires per-route risk acknowledgement; `secret` data is never sent and `ask` fields are never approved automatically;
- automatic pull is off by default and requires per-account acknowledgement; ordinary capture extracts user messages, while probe answers remain low-confidence candidates;
- `prepared` means content was generated; it enters `dispatching` before the click, `sent_unconfirmed` after the click, and `completed` only after local acknowledgement;
- a failed page adapter stops safely and does not click unknown elements.

The registry covers 18 global and Chinese web providers; see the [provider adapter matrix](PROVIDERS.en.md). DOM adapters can fall back to copy mode when a provider changes its page. Interactive attachment transfer still requires a provider-specific picker or official API.
