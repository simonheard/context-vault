# Versioning and compatibility sync

[中文](VERSIONING.md)

ContextVault versions the Python product, SQLite schema, client protocol, and each adapter independently. The current set is product `0.9.0`, schema `8`, protocol `2`, and Chrome extension `0.2.0`.

- `/api/version` performs a handshake before routes are read;
- the extension sends `X-ContextVault-Protocol`, and values outside the server range receive HTTP 426;
- `sync_clients` records extension or future device-client versions, protocol, status, and last seen time;
- `sync_events.protocol_version` lets newer clients identify older event formats;
- `schema_migrations` and idempotent column migration upgrade older vaults in place;
- CLI managed blocks match and replace older protocol markers in place;
- profiles and receipts use content-hash versions, and diff is based only on the last completed receipt;
- protocol-1 extensions remain usable inside the compatibility window; clients below the minimum must upgrade, while clients newer than the server require a server upgrade.

Back up `vault.sqlite` before database upgrades. For a protocol increase, first release a server that reads old and new formats, then update clients, and only raise the minimum protocol in a later major release to avoid coordinated downtime.
