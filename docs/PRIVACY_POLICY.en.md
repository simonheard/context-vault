# Sensitive-data Sync and Informed Consent

[中文](PRIVACY_POLICY.md)

## Goal

Let users intentionally synchronize sensitive information without reducing the
decision to one global switch and a blanket disclaimer. Informed consent must
identify the target, categories, risks, scope, and limits of revocation.

## Control hierarchy

### Global master switch

`Allow sensitive-data sync` is off by default. When off, every target is forced
to `block`.

### Target switch

Gemini, Claude, ChatGPT, and other providers are configured separately. Enabling
Gemini never enables another provider.

### Category switch

Sensitive categories include at least:

- health and medical;
- financial;
- legal and immigration;
- precise address and location;
- government identifiers and official documents;
- family and relationships;
- confidential work information;
- device identifiers, network details, and detailed configuration.

Each category offers:

- `block` — never send;
- `ask` — confirm every time;
- `allow` — permit automatic synchronization.

Secret-class data never exposes `allow` and is always rejected.

## First-time enablement

1. Identify the target provider and account label.
2. Show the categories being enabled with concrete examples.
3. Explain that data will leave the local device and be processed by a third party.
4. Explain that retention and use depend on the provider's policies and settings.
5. Explain that disabling sync stops future sends but may not delete prior data.
6. Provide a complete preview with per-item removal.
7. Require an active checkbox; never preselect consent.
8. Store a `ConsentReceipt` containing the notice version, choices, target, and time.

## Suggested risk notice

> You are about to send selected personal information to a third-party AI
> provider. It may include health, financial, legal, location, family, work, or
> device information. After sending, the data is governed by that provider's
> privacy policy, retention practices, and account settings. ContextVault can
> stop future synchronization and record what was sent, but it cannot guarantee
> that the provider deletes or forgets information it has already received.
> Review the fields below and send only information you are willing to let that
> provider process.

The action label should be specific, such as `Allow Gemini to sync the selected
sensitive information`, rather than merely `Agree` or `Continue`.

## Suggested disclaimer

> ContextVault provides local organization, filtering, and synchronization
> tools. It does not represent or control target AI providers or their handling
> of previously transmitted data. Automatic detection and sensitivity
> classification may be incorrect; users should review the synchronization
> preview before sending. ContextVault is not designed to store or transmit
> passwords, OTPs, private keys, API keys, cookies, or other authentication
> secrets. Carefully consider whether medical, legal, financial, or personal
> safety information needs to be sent.

This is product-language guidance, not legal advice. Before public release, the
actual data flow, operating regions, and business model require privacy and
legal review.

## Per-sync interface

The preview shows:

- target provider and account;
- added, changed, removed, and expired information;
- sensitivity level for each item;
- separate confirmation for `ask` categories;
- fields blocked or redacted by policy;
- the final text or file the target will receive;
- previous sync time and version diff.

## Revocation and correction

After revocation:

- block future synchronization immediately;
- cancel pending tasks;
- preserve immutable consent and sync audit records;
- generate provider-specific correction or deletion guidance;
- never claim remote deletion unless the provider confirms it.

## Re-consent triggers

- adding a sensitive category;
- changing the target account;
- changing from `ask` to `allow`;
- a material change to the risk notice or provider data policy;
- re-enabling after a long inactive period;
- materially expanding scope or automation.

