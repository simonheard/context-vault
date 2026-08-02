from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from contextvault import __version__
from contextvault.vault import initialize, status
from contextvault.gui import serve
from contextvault.domain import ClaimStatus, Sensitivity, SourceType
from contextvault.repository import VaultRepository
from contextvault.services import ProfileService, claim_to_dict


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

    accounts_parser = subparsers.add_parser("accounts", help="manage AI provider accounts")
    account_commands = accounts_parser.add_subparsers(dest="account_command", required=True)
    account_commands.add_parser("list", help="list provider accounts")
    account_add = account_commands.add_parser("add", help="add a provider account reference")
    account_add.add_argument("--platform", required=True, choices=["chatgpt", "gemini", "claude", "other"])
    account_add.add_argument("--label", required=True)

    spaces_parser = subparsers.add_parser("spaces", help="manage profile spaces")
    space_commands = spaces_parser.add_subparsers(dest="space_command", required=True)
    space_commands.add_parser("list", help="list profile spaces")
    space_add = space_commands.add_parser("add", help="add a profile space")
    space_add.add_argument("--name", required=True)
    space_add.add_argument("--display-name", required=True)

    claims_parser = subparsers.add_parser("claims", help="manage profile claims")
    claim_commands = claims_parser.add_subparsers(dest="claim_command", required=True)
    claim_list = claim_commands.add_parser("list", help="list claims")
    claim_list.add_argument("--status", choices=[item.value for item in ClaimStatus])
    claim_list.add_argument("--space")
    claim_add = claim_commands.add_parser("add", help="add a manual claim candidate")
    claim_add.add_argument("attribute")
    claim_add.add_argument("value")
    claim_add.add_argument("--space", default="personal")
    claim_add.add_argument("--confidence", type=float, default=1.0)
    claim_add.add_argument(
        "--sensitivity",
        choices=[item.value for item in Sensitivity],
        default=Sensitivity.PERSONAL.value,
    )
    claim_confirm = claim_commands.add_parser("confirm", help="confirm a candidate claim")
    claim_confirm.add_argument("claim_id")
    claim_reject = claim_commands.add_parser("reject", help="reject a candidate claim")
    claim_reject.add_argument("claim_id")

    profile_parser = subparsers.add_parser("profile", help="render the canonical profile")
    profile_commands = profile_parser.add_subparsers(dest="profile_command", required=True)
    profile_show = profile_commands.add_parser("show", help="show confirmed profile claims")
    profile_show.add_argument("--space", default="personal")
    profile_show.add_argument("--format", choices=["markdown", "json"], default="markdown")

    events_parser = subparsers.add_parser("events", help="inspect the append-only sync log")
    event_commands = events_parser.add_subparsers(dest="event_command", required=True)
    event_list = event_commands.add_parser("list", help="list sync events")
    event_list.add_argument("--after", type=int, default=0)

    attachments_parser = subparsers.add_parser(
        "attachments", help="manage provider-hosted attachment references"
    )
    attachment_commands = attachments_parser.add_subparsers(
        dest="attachment_command", required=True
    )
    attachment_list = attachment_commands.add_parser(
        "list", help="list attachment references"
    )
    attachment_list.add_argument("--account")
    attachment_add = attachment_commands.add_parser(
        "add", help="add an attachment reference without copying the file"
    )
    attachment_add.add_argument("--account", required=True)
    attachment_add.add_argument("--provider-file-id", required=True)
    attachment_add.add_argument("--filename", required=True)
    attachment_add.add_argument("--url")
    attachment_add.add_argument("--mime-type")
    attachment_add.add_argument(
        "--sensitivity",
        choices=[item.value for item in Sensitivity],
        default=Sensitivity.PRIVATE.value,
    )
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
            print(f"Attachment references: {vault_status.attachment_count}")
            print(f"Sync events: {vault_status.sync_event_count}")
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
        if args.command in {
            "accounts",
            "spaces",
            "claims",
            "profile",
            "events",
            "attachments",
        }:
            repository = VaultRepository(args.vault)
            service = ProfileService(repository)
            if args.command == "accounts":
                if args.account_command == "add":
                    account = repository.add_account(args.platform, args.label)
                    print(f"Added account: {account.id} ({account.account_label})")
                    return 0
                for account in repository.list_accounts():
                    print(f"{account.id}\t{account.platform}\t{account.account_label}\t{account.status}")
                return 0
            if args.command == "spaces":
                if args.space_command == "add":
                    space = repository.add_space(args.name, args.display_name)
                    print(f"Added space: {space.id} ({space.name})")
                    return 0
                for space in repository.list_spaces():
                    default = "\tdefault" if space.is_default else ""
                    print(f"{space.id}\t{space.name}\t{space.display_name}{default}")
                return 0
            if args.command == "claims":
                if args.claim_command == "add":
                    claim = service.add_candidate(
                        attribute=args.attribute,
                        value=args.value,
                        space=args.space,
                        confidence=args.confidence,
                        sensitivity=Sensitivity(args.sensitivity),
                        source_type=SourceType.MANUAL,
                    )
                    print(f"Added candidate: {claim.id}")
                    return 0
                if args.claim_command == "confirm":
                    claim = service.confirm(args.claim_id)
                    print(f"Confirmed claim: {claim.id}")
                    return 0
                if args.claim_command == "reject":
                    claim = service.reject(args.claim_id)
                    print(f"Rejected claim: {claim.id}")
                    return 0
                selected_status = ClaimStatus(args.status) if args.status else None
                claims = repository.list_claims(status=selected_status, space=args.space)
                print(json.dumps([claim_to_dict(claim) for claim in claims], ensure_ascii=False, indent=2))
                return 0
            if args.command == "profile":
                if args.format == "json":
                    print(json.dumps(service.current_profile(args.space), ensure_ascii=False, indent=2))
                else:
                    print(service.markdown_profile(args.space))
                return 0
            if args.command == "events":
                events = repository.list_events(after_sequence=args.after)
                print(
                    json.dumps(
                        [
                            {
                                "sequence": event.sequence,
                                "event_id": event.event_id,
                                "device_id": event.device_id,
                                "event_type": event.event_type,
                                "aggregate_type": event.aggregate_type,
                                "aggregate_id": event.aggregate_id,
                                "payload": event.payload,
                                "created_at": event.created_at,
                            }
                            for event in events
                        ],
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return 0
            if args.command == "attachments":
                if args.attachment_command == "add":
                    attachment = repository.add_attachment_ref(
                        account_id=args.account,
                        provider_file_id=args.provider_file_id,
                        filename=args.filename,
                        remote_url=args.url,
                        mime_type=args.mime_type,
                        sensitivity=Sensitivity(args.sensitivity),
                    )
                    print(f"Added attachment reference: {attachment.id}")
                    return 0
                attachments = repository.list_attachment_refs(args.account)
                print(
                    json.dumps(
                        [
                            {
                                "id": item.id,
                                "account_id": item.account_id,
                                "provider_file_id": item.provider_file_id,
                                "filename": item.filename,
                                "remote_url": item.remote_url,
                                "mime_type": item.mime_type,
                                "sensitivity": item.sensitivity.value,
                                "status": item.status,
                            }
                            for item in attachments
                        ],
                        ensure_ascii=False,
                        indent=2,
                    )
                )
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
