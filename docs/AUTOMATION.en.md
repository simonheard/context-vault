# Full automation

[中文](AUTOMATION.md)

## Modes

- `manual`: generate a package or copy text;
- semi-automatic: preview and fill the composer, with the user clicking Send;
- `full`: every five minutes, the extension checks for due routes with a diff, reuses or opens the target page, fills the composer, and clicks an explicitly recognized send button.

Full automation is off by default. Enabling it requires per-route acknowledgement that the browser may be signed in to the wrong account, the provider may retain or analyze sent data, page changes can cause failures, and disabling automation cannot retract earlier sends.

```bash
contextvault routes automation <route-id> \
  --mode full --interval 60 --acknowledge-data-risk
```

## Controls that automation cannot bypass

- `secret` data is never stored or sent;
- private/sensitive data remains blocked while the global sensitive gate is off;
- `ask` fields never enter unattended jobs;
- `allow` private fields still require active consent matching the target account and category;
- no diff means no send, and a prepared receipt prevents duplicate sends;
- a missing composer or explicit send button stops safely; failed receipts remain auditable and retryable;
- automation never scrapes cookies or simulates provider login on a server.

`contextvault daemon install` installs the loopback API as a macOS LaunchAgent, Linux systemd user service, or Windows logon task. After one-time installation and extension pairing, normal operation requires only that the user stay signed in; the local service and extension resume at OS login and Chrome startup.

DOM automation cannot prove that a provider understood or permanently retained the profile. `completed` means the extension clicked a recognized Send control; it is not proof of remote ingestion or deletion.

## Why a userscript is not the primary implementation

A Chrome MV3 extension centralizes minimum host permissions, browser-managed local storage and alarms, protocol negotiation, and upgrades. A userscript adds another script manager and makes permissions, update state, and multi-provider selectors harder to audit. Because the extension implements full automation, ContextVault does not ship a duplicate higher-risk userscript. A provider-specific, disabled-by-default fallback should be considered only if a site blocks extension content scripts and offers no official API.
