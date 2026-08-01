# ContextVault

[中文](README.md)

ContextVault is a local-first, user-owned context store for AI work. It converts
exports from different AI products into a searchable, auditable, and portable
format, with an explicit review step before anything is sent to another
provider.

> Your AI context belongs to you, not to one AI provider.

## Product boundary

This project does not promise to automatically sync every chat or recreate
another provider's native conversation list. The first stage focuses on stable
official exports, a normalized model, local search, sensitivity checks, and
portable context packages. Browser capture and end-to-end encrypted
multi-device sync come after the core workflow is validated.

## Product principles

- **Local-first:** Parsing, indexing, and review happen on the user's device by default.
- **Explicit consent:** Show exactly what will be stored or sent before the action occurs.
- **Traceable:** Every memory retains provenance, time, confidence, scope, sensitivity, and lifecycle state.
- **Adapter isolation:** Vendor format changes stay outside the internal domain model.
- **No credentials:** Store references to credentials, never passwords, keys, or session tokens.
- **Honest portability:** Make history searchable and usable as context without claiming native restoration.

## Current status

This is the planning and bootstrap milestone. It includes:

- a zero-dependency Python CLI;
- a SQLite vault with FTS5 support;
- product, architecture, and risk documentation;
- tests for vault initialization and status.

## Quick start

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
contextvault init
contextvault status
contextvault doctor
python3 -m unittest discover -s tests
```

The default vault is `.contextvault/vault.sqlite`; override it with
`--vault PATH`.

## Command roadmap

```text
contextvault init
contextvault status
contextvault doctor
contextvault import <export.zip> --source chatgpt|claude|gemini
contextvault inspect
contextvault search <query>
contextvault extract-memories
contextvault redact
contextvault export --target markdown|json|claude|gemini|chatgpt
```

Only `init`, `status`, and `doctor` are implemented in this bootstrap.

## Documentation

- [Product plan](docs/PRODUCT_PLAN.en.md)
- [Architecture](docs/ARCHITECTURE.en.md)

