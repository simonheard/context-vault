# ContextVault

[中文](README.md)

ContextVault is a **personal memory and profile synchronization tool for AI
assistants**.

It discovers what ChatGPT, Gemini, Claude, and other assistants have learned
about a user, turns that information into a continuously maintained and
traceable personal profile, and synchronizes approved parts to other AI tools.

Examples include:

- age, birthday, location, and languages;
- school, major, employer, role, and skills;
- response style, writing, food, and travel preferences;
- active projects, long-term goals, and prior decisions;
- computers, phones, servers, and smart devices;
- hardware, operating systems, software, development environments, and
  non-sensitive configuration for each device.

> Let every AI know the same you, within boundaries you control.

## Not a chat backup tool

Raw conversations are only one source. The product does not copy every chat to
another platform; it maintains a structured, verifiable personal memory profile
that changes over time.

```text
ChatGPT history       Device scan       Manual input       Other sources
        \                  |                 |                 /
         ----> extraction, change detection, conflict resolution <----
                                  |
                                  v
                      Profile + device environment
                                  |
                       review and sync policies
                          /       |        \
                         v        v         v
                      Gemini   Claude   other AI tools
```

## Core capabilities

1. **Automatic discovery:** Extract facts, preferences, relationships, goals, and environment details from long-running conversations.
2. **Continuous updates:** Understand changes such as a new job, move, or computer instead of accumulating stale facts.
3. **Provenance and time:** Keep the source conversation, timestamp, confidence, and validity period for every claim.
4. **Conflict resolution:** Merge, expire, or ask for confirmation when new information conflicts with old information.
5. **Device synchronization:** Collect approved hardware, OS, software, and configuration details without collecting secrets.
6. **Automatic summaries:** Generate a short bio, full profile, project pack, or device environment report.
7. **Per-target policies:** Choose fields, sensitivity limits, and frequency separately for Gemini, Claude, and other targets.
8. **Privacy-first:** Process locally by default; require confirmation for sensitive data and first-time cross-platform sharing.
9. **Sensitive-data controls:** Set never, ask every time, or allow automatic sync separately for each provider and category.
10. **Multi-account isolation:** Route personal, work, and client accounts separately to prevent data mixing.
11. **Local management UI:** Manage profiles, accounts, spaces, devices, privacy, and sync history in one simple dashboard.

## First complete workflow

The MVP is not primarily full-text search. Its first closed loop is:

```text
Import ChatGPT data
  -> extract profile candidates
  -> one-time user review
  -> build a canonical personal profile
  -> generate a Gemini-ready profile summary
  -> incrementally update it as conversations change
```

The first release prioritizes:

- ChatGPT official export parsing;
- identity, education, employment, location, preference, skill, project, and device extraction;
- candidate review and conflict resolution;
- Markdown and JSON personal profiles;
- Gemini profile packages and copy/injection workflows;
- local device inventory;
- change summaries and sync previews.

## Repository status

This repository currently contains the product and data-model foundation:

- a zero-dependency Python CLI;
- a SQLite store centered on `Entity`, `Claim`, `Device`, and `SyncTarget`;
- a personal information model, roadmap, security boundaries, and architecture;
- vault initialization and status tests.

## Quick start

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
contextvault init
contextvault status
contextvault doctor
contextvault ui
python3 -m unittest discover -s tests
```

## Planned commands

```text
contextvault import chatgpt-export.zip
contextvault extract-profile
contextvault review
contextvault profile show
contextvault devices scan
contextvault diff
contextvault sync add gemini
contextvault sync preview gemini
contextvault sync run gemini
contextvault privacy show
contextvault privacy set --target gemini --sensitive ask
contextvault accounts list
contextvault routes preview <route>
contextvault summary --type personal
contextvault summary --type devices
```

## Documentation

- [Product plan](docs/PRODUCT_PLAN.en.md)
- [Architecture](docs/ARCHITECTURE.en.md)
- [Profile and memory model](docs/MEMORY_MODEL.en.md)
- [Sensitive-data sync and informed consent](docs/PRIVACY_POLICY.en.md)
- [Multi-account design](docs/MULTI_ACCOUNT.en.md)
- [Design recommendations and priorities](docs/DESIGN_RECOMMENDATIONS.en.md)
- [Local management UI](docs/GUI.en.md)
