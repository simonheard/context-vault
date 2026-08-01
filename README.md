# aimem

Portable AI memory and context tools. `aimem` turns exports from AI products
into a local, searchable, auditable context store that the user controls.

The product is deliberately narrower than “sync every chat everywhere.” The
first milestone focuses on stable official exports, a normalized data model,
local search, redaction, and portable Markdown/JSON packages. Browser capture
and encrypted multi-device sync come later.

## Product principles

- Local-first: parsing, indexing, and review happen on the user's device.
- Explicit consent: users preview what will be stored or sent to another AI.
- Traceable memory: every extracted fact keeps source, time, confidence, scope,
  sensitivity, and lifecycle state.
- Adapter-based: vendor-specific import and export formats stay isolated.
- No credentials: store credential references, never secrets.
- Honest portability: make history searchable and usable as context; do not
  promise to recreate another provider's native conversation list.

## Repository status

This is the planning and bootstrap milestone. It includes:

- a zero-dependency Python CLI skeleton;
- a SQLite vault schema with FTS5 search support;
- product scope, architecture, risks, and milestones;
- tests for vault creation and status reporting.

## Quick start

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
aimem init
aimem status
aimem doctor
python3 -m unittest discover -s tests
```

The default vault is `.aimem/vault.sqlite`. Override it with `--vault PATH`.

## Initial command roadmap

```text
aimem init
aimem status
aimem doctor
aimem import <export.zip> --source chatgpt|claude|gemini
aimem inspect
aimem search <query>
aimem extract-memories
aimem redact
aimem export --target markdown|json|claude|gemini|chatgpt
```

Only `init`, `status`, and `doctor` are implemented in this bootstrap.

See [docs/PRODUCT_PLAN.md](docs/PRODUCT_PLAN.md) and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

