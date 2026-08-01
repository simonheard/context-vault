# Local Management UI

[中文](GUI.md)

## Positioning

The dashboard is the primary control surface for an ordinary user, not a server
administrator console. It binds to `127.0.0.1` by default, reads the local vault,
and is not deployed publicly.

## Current runnable prototype

```bash
contextvault ui
```

Then open `http://127.0.0.1:8787`.

The current implementation provides:

- vault counts for claims, candidates, accounts, devices, spaces, routes, and receipts;
- provider account listing and local account-reference creation;
- identity-space listing and creation;
- interface structure for profiles, routes, devices, privacy, and history;
- responsive desktop and mobile layout;
- loopback-only binding that rejects public addresses.

## Information architecture

### Overview

- confirmed claims, review queue, AI accounts, and devices;
- profile health;
- what each provider account knows;
- recent changes and sync state;
- high-risk and conflict alerts.

### Profile

- identity, education, employment, preference, skill, project, relationship, and event categories;
- candidate, confirmed, conflicted, expired, and rejected filters;
- provenance, confidence, time, and sensitivity;
- batch confirmation, edit, expiration, and rejection.

### AI accounts

- personal, work, and client accounts;
- account state and last recognition time;
- local labels without authentication secrets;
- disconnect, revoke, and re-identify.

### Identity spaces and routes

- personal, work, client, and anonymous spaces;
- visual source account, space, and destination account;
- category, sensitivity, and automation policy per route.

### Devices

- model, OS, development tools, and last scan;
- scan diffs;
- collection allowlists;
- explicit display of rejected secret categories.

### Privacy and consent

- global sensitive-sync control;
- block, ask, and allow per account and category;
- notice and disclaimer versions;
- consent receipts, revocation, and re-consent.

### Sync history

- added, changed, expired, and deleted diffs;
- target provider and exact account;
- actual payload and claim manifest;
- verification, correction, and revocation status.

## Security constraints

- local-only by default;
- request-size limits and validation on all mutations;
- never read or display passwords, cookies, or tokens;
- require authentication, TLS, and CSRF protection before any LAN access;
- never expose the local console directly as a public multi-user SaaS.

