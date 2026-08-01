from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from contextvault import __version__
from contextvault.vault import initialize, status
from contextvault.gui import serve


DEFAULT_VAULT = Path(".contextvault/vault.sqlite")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextvault",
        description="Personal memory and profile sync across AI assistants",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--vault", type=Path, default=DEFAULT_VAULT, help="path to the SQLite vault"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="initialize a local vault")
    subparsers.add_parser("status", help="show local vault status")
    subparsers.add_parser("doctor", help="check local runtime capabilities")
    ui_parser = subparsers.add_parser("ui", help="start the local management UI")
    ui_parser.add_argument("--host", default="127.0.0.1")
    ui_parser.add_argument("--port", type=int, default=8787)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            vault_status = initialize(args.vault)
            print(f"Initialized vault: {vault_status.path}")
            print(f"Schema version: {vault_status.schema_version}")
            return 0
        if args.command == "status":
            vault_status = status(args.vault)
            print(f"Vault: {vault_status.path}")
            print(f"Schema version: {vault_status.schema_version}")
            print(f"Claims: {vault_status.claim_count}")
            print(f"Devices: {vault_status.device_count}")
            print(f"Provider accounts: {vault_status.account_count}")
            print(f"Profile spaces: {vault_status.profile_space_count}")
            print(f"Sync routes: {vault_status.sync_route_count}")
            print(f"Sync targets: {vault_status.sync_target_count}")
            return 0
        if args.command == "doctor":
            sqlite_version = sqlite3.sqlite_version
            fts5 = _has_fts5()
            print(f"Python: {sys.version.split()[0]}")
            print(f"SQLite: {sqlite_version}")
            print(f"FTS5: {'available' if fts5 else 'unavailable'}")
            return 0 if fts5 else 1
        if args.command == "ui":
            if args.host not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("The management UI may only bind to a loopback host")
            serve(args.vault, args.host, args.port)
            return 0
    except (FileNotFoundError, OSError, sqlite3.Error, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 2


def _has_fts5() -> bool:
    try:
        with sqlite3.connect(":memory:") as connection:
            connection.execute("CREATE VIRTUAL TABLE probe USING fts5(content)")
    except sqlite3.Error:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
