# User-session browser extension

[中文](BROWSER_EXTENSION.md)

## How it works

The extension uses ChatGPT, Gemini, or Claude pages where the user is already signed in through Chrome. ContextVault never reads, stores, or uploads passwords, cookies, OAuth tokens, or sessions. The extension only:

1. identifies the supported provider and checks that a composer is available;
2. reads the configured route preview from `127.0.0.1:8787`;
3. displays final text, policy-blocked fields, and sensitive fields requiring per-run approval;
4. requires the user to confirm that the page is signed in to the route's target account;
5. fills the approved text into the composer without clicking Send;
6. lets the user acknowledge a `prepared` receipt as `completed` after manually sending.

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
6. Sign in normally to ChatGPT, Gemini, or Claude, open a conversation, and select the extension icon.

Run `contextvault extension rotate-token` when an already paired extension is no longer trusted. Every old token becomes invalid immediately, and retained extensions must pair again with the new token.

## Preparation

Create at least one target account and route:

```bash
contextvault accounts add --platform gemini --label "Personal Gemini"
contextvault routes add --space personal --to <gemini-account-id>
```

The extension shows only enabled routes whose target provider matches the current page. With multiple accounts on one provider, it never guesses the active identity; the user must confirm the target account label before every fill operation.

## Security boundary

- the API remains loopback-only by default;
- extension requests require a random vault pairing token;
- the token lives in Chrome extension local storage and is not a provider credential;
- the extension never reads cookies, scrapes conversation history, or simulates server-side login;
- it does not send automatically or auto-approve `ask` sensitivity fields;
- `prepared` means content was generated or filled; only user acknowledgement after sending makes it `completed`;
- a failed page adapter stops safely and does not click unknown elements.

Composer filling currently supports ChatGPT, Gemini, and Claude. Interactive attachment transfer still requires a provider-specific file picker or official upload API; the extension does not bypass browser file permissions.
