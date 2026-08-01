# Multi-account Design

[中文](MULTI_ACCOUNT.md)

## Goal

One user may have personal and work accounts on ChatGPT, Gemini, Claude, and
other providers. The system must know which account supplied each piece of
evidence, which account received each sync, and prevent accidental data mixing.

## Core model

```text
ProviderAccount (source)
        |
        v
ProfileSpace (personal / work / client / anonymous)
        |
        v
Canonical Claims
        |
        v
SyncRoute + Policy
        |
        v
ProviderAccount (target)
```

### ProviderAccount

A reference to one provider account:

- provider: ChatGPT, Gemini, Claude, or another platform;
- local label: `Personal Gemini` or `Company ChatGPT`;
- optional irreversible account-identifier hash;
- state: active, disconnected, or revoked;
- last recognized and synchronized times.

Passwords, cookies, OAuth tokens, and sessions are not stored. Authentication
remains in the browser or a future system credential store.

### ProfileSpace

An isolation boundary such as:

- `personal`: personal life and general preferences;
- `work`: current employer, company devices, and internal projects;
- `client/acme`: information for one client;
- `anonymous`: preferences without real identity.

A claim may belong to one or more explicitly allowed spaces, but accounts are
never mixed merely because the same person owns them.

### SyncRoute

Defines source, profile space, and destination:

```text
Personal ChatGPT -> personal -> Personal Gemini
Work ChatGPT -> work -> Company Gemini
MacBook agent -> personal + selected work fields -> selected targets
```

Each route has its own category allowlist, sensitivity mode, automatic-sync
setting, and summary budget.

## Account recognition

Before writing, the extension shows the provider and local account label. When
it detects an account change, it pauses and asks for confirmation rather than
assuming the account is unchanged because the domain is the same.

Email addresses are displayed locally only when needed. Persistent identity
should prefer an irreversible hash plus a user-defined label.

## Anti-mixing rules

1. A new account has no sync route by default.
2. A work space cannot sync to a personal account by default.
3. Sensitive consent never transfers between accounts.
4. Changing a destination account requires new consent.
5. Every preview shows the target provider and account label.
6. Every sync receipt binds to a specific account and route.
7. Automatic writes stop when the current web account cannot be verified.

## Account lifecycle

- **Connect:** create a local reference and select spaces; do not sync history immediately.
- **Rename:** change only the local label, not identity.
- **Disconnect:** stop reads and writes while preserving audit records.
- **Revoke:** disable routes and consent; remote data may still exist.
- **Delete local reference:** first resolve associated sources, receipts, and correction tasks.

## Planned commands

```text
contextvault accounts list
contextvault accounts add chatgpt --label personal-chatgpt
contextvault accounts rename <id> --label work-chatgpt
contextvault accounts disconnect <id>
contextvault spaces list
contextvault spaces create work
contextvault routes add --from <account> --space work --to <account>
contextvault routes preview <route>
```

