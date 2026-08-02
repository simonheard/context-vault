from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sqlite3
import sys
from pathlib import Path

from contextvault import __version__
from contextvault.vault import initialize, status
from contextvault.gui import browser_vault_payload, serve
from contextvault.domain import ClaimStatus, Sensitivity, SourceType
from contextvault.repository import VaultRepository
from contextvault.services import ProfileService, claim_to_dict
from contextvault.device_agent import scan_device
from contextvault.pipeline import ImportPipeline
from contextvault.summaries import SummaryService
from contextvault.sync_service import SyncService
from contextvault.providers import PROVIDERS, provider_capabilities
from contextvault.cli_adapters import CLI_TOOLS, CliAdapterService
from contextvault.daemon_service import daemon_status, install_daemon, uninstall_daemon
from contextvault.summary_engines import SummaryEngineService
from contextvault.capture_service import CaptureService


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
    link_parser = subparsers.add_parser("link", help="link the standalone extension with a short one-time code")
    link_parser.add_argument("--host", default="127.0.0.1")
    link_parser.add_argument("--port", type=int, default=8787)
    link_parser.add_argument("--ttl", type=int, default=600)
    link_parser.add_argument("--code-only", action="store_true", help="print a code for an already running local service")

    accounts_parser = subparsers.add_parser("accounts", help="manage AI provider accounts")
    account_commands = accounts_parser.add_subparsers(dest="account_command", required=True)
    account_commands.add_parser("list", help="list provider accounts")
    account_add = account_commands.add_parser("add", help="add a provider account reference")
    account_add.add_argument("--platform", required=True, choices=[*PROVIDERS, "other"])
    account_add.add_argument("--label", required=True)
    account_rename = account_commands.add_parser("rename", help="rename a local account label")
    account_rename.add_argument("account_id")
    account_rename.add_argument("--label", required=True)
    for action in ("disconnect", "revoke"):
        action_parser = account_commands.add_parser(action, help=f"{action} an account reference")
        action_parser.add_argument("account_id")

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
    claim_confirm_all = claim_commands.add_parser("confirm-all", help="confirm all candidates")
    claim_confirm_all.add_argument("--space")
    claim_delete = claim_commands.add_parser("delete", help="permanently delete a local claim")
    claim_delete.add_argument("claim_id")
    claim_search = claim_commands.add_parser("search", help="full-text search claims")
    claim_search.add_argument("query")

    profile_parser = subparsers.add_parser("profile", help="render the canonical profile")
    profile_commands = profile_parser.add_subparsers(dest="profile_command", required=True)
    profile_show = profile_commands.add_parser("show", help="show confirmed profile claims")
    profile_show.add_argument("--space", default="personal")
    profile_show.add_argument("--format", choices=["markdown", "json"], default="markdown")
    profile_health = profile_commands.add_parser("health", help="show profile health and review counts")
    profile_health.add_argument("--space", default="personal")
    profile_export_browser = profile_commands.add_parser("export-browser", help="export a standalone extension backup")
    profile_export_browser.add_argument("output", type=Path)
    profile_export_browser.add_argument("--space", default="personal")

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

    import_parser = subparsers.add_parser("import", help="import provider data exports")
    import_parser.add_argument("source", type=Path, help="ChatGPT export or standalone browser-vault JSON")
    import_parser.add_argument("--format", choices=["auto", "chatgpt", "browser-vault"], default="auto")
    import_parser.add_argument("--account")
    import_parser.add_argument("--space", default="personal")
    import_parser.add_argument("--no-extract", action="store_true")

    imports_parser = subparsers.add_parser("imports", help="list completed source imports")
    imports_parser.add_argument("list", nargs="?")

    devices_parser = subparsers.add_parser("devices", help="scan and list local devices")
    device_commands = devices_parser.add_subparsers(dest="device_command", required=True)
    device_commands.add_parser("list", help="list known devices")
    device_scan = device_commands.add_parser("scan", help="scan approved non-secret metadata")
    device_scan.add_argument("--name")

    routes_parser = subparsers.add_parser("routes", help="manage account sync routes")
    route_commands = routes_parser.add_subparsers(dest="route_command", required=True)
    route_commands.add_parser("list", help="list routes")
    route_add = route_commands.add_parser("add", help="add source-space-target route")
    route_add.add_argument("--from", dest="source_account")
    route_add.add_argument("--space", default="personal")
    route_add.add_argument("--to", dest="target_account", required=True)
    route_add.add_argument("--categories", default="*")
    route_add.add_argument(
        "--max-sensitivity",
        choices=[item.value for item in Sensitivity if item is not Sensitivity.SECRET],
        default="personal",
    )
    route_add.add_argument("--sensitive", choices=["block", "ask", "allow"], default="block")
    route_add.add_argument("--budget", type=int, default=12000)
    route_add.add_argument(
        "--attachments",
        choices=["exclude", "reference", "extracted_text", "transfer"],
        default="reference",
    )
    route_preview = route_commands.add_parser("preview", help="preview filtered content and diff")
    route_preview.add_argument("route_id")
    route_preview.add_argument("--approve-sensitive", action="store_true")
    route_disable = route_commands.add_parser("disable", help="disable a sync route")
    route_disable.add_argument("route_id")
    route_automation = route_commands.add_parser(
        "automation", help="configure unattended browser synchronization"
    )
    route_automation.add_argument("route_id")
    route_automation.add_argument("--mode", choices=["manual", "full"], required=True)
    route_automation.add_argument("--interval", type=int, default=60)
    route_automation.add_argument("--acknowledge-data-risk", action="store_true")

    sync_parser = subparsers.add_parser("sync", help="create a local sync package and receipt")
    sync_commands = sync_parser.add_subparsers(dest="sync_command", required=True)
    sync_run = sync_commands.add_parser("run", help="finalize an approved sync package")
    sync_run.add_argument("route_id")
    sync_run.add_argument("--approve-sensitive", action="store_true")
    sync_run.add_argument("--output", type=Path, help="write the generated Markdown package")
    sync_commands.add_parser("receipts", help="list sync receipts")
    sync_acknowledge = sync_commands.add_parser(
        "acknowledge", help="mark a prepared receipt as sent by the user"
    )
    sync_acknowledge.add_argument("receipt_id")

    privacy_parser = subparsers.add_parser("privacy", help="manage sensitive-data consent")
    privacy_commands = privacy_parser.add_subparsers(dest="privacy_command", required=True)
    privacy_commands.add_parser("enable-sensitive", help="enable the global sensitive-data gate")
    privacy_commands.add_parser("disable-sensitive", help="disable the global sensitive-data gate")
    privacy_consent = privacy_commands.add_parser("consent", help="record informed consent for a route")
    privacy_consent.add_argument("route_id")
    privacy_consent.add_argument("--categories", required=True)
    privacy_consent.add_argument("--mode", choices=["ask", "allow"], required=True)
    privacy_revoke = privacy_commands.add_parser("revoke", help="revoke a consent receipt")
    privacy_revoke.add_argument("consent_id")

    summary_parser = subparsers.add_parser("summary", help="render a purpose-specific summary")
    summary_parser.add_argument(
        "--type", choices=["personal", "full", "work", "project", "devices", "recent"], required=True
    )
    summary_parser.add_argument("--space", default="personal")
    summary_parser.add_argument(
        "--engine",
        choices=["deterministic", "ollama", "lmstudio", "openai-compatible", "codex-cli", "claude-code"],
        default="deterministic",
    )
    summary_parser.add_argument("--model")
    summary_parser.add_argument("--base-url")
    summary_parser.add_argument("--api-key-env")
    summary_parser.add_argument("--allow-cloud", action="store_true")
    summary_parser.add_argument("--max-chars", type=int, default=12000)

    models_parser = subparsers.add_parser("models", help="detect optional local and signed-in summary engines")
    models_parser.add_argument("detect", nargs="?")

    captures_parser = subparsers.add_parser("captures", help="manage automatic conversation capture")
    capture_commands = captures_parser.add_subparsers(dest="capture_command", required=True)
    capture_commands.add_parser("list", help="list configured browser capture sources")
    capture_enable = capture_commands.add_parser("enable", help="enable capture for a provider account")
    capture_enable.add_argument("account_id")
    capture_enable.add_argument("--interval", type=int, default=15)
    capture_enable.add_argument("--conversation-url")
    capture_enable.add_argument("--acknowledge-privacy-risk", action="store_true")
    capture_disable = capture_commands.add_parser("disable", help="disable capture for a provider account")
    capture_disable.add_argument("account_id")

    extension_parser = subparsers.add_parser(
        "extension", help="pair the user-side browser extension"
    )
    extension_commands = extension_parser.add_subparsers(
        dest="extension_command", required=True
    )
    extension_commands.add_parser("token", help="show the local pairing token")
    extension_commands.add_parser(
        "rotate-token", help="revoke paired extensions and issue a new token"
    )
    subparsers.add_parser("providers", help="show available user-side provider adapters")

    cli_parser = subparsers.add_parser("cli", help="sync profiles into coding-agent context files")
    cli_commands = cli_parser.add_subparsers(dest="cli_command", required=True)
    cli_commands.add_parser("list", help="list supported coding CLI tools")
    cli_commands.add_parser("status", help="list installed context-file adapters")
    cli_install = cli_commands.add_parser("install", help="install or update a managed context block")
    cli_install.add_argument("tool", choices=list(CLI_TOOLS))
    cli_install.add_argument("--scope", choices=["project", "global"], default="project")
    cli_install.add_argument("--directory", type=Path, default=Path.cwd())
    cli_install.add_argument("--space", default="personal")
    cli_install.add_argument(
        "--summary-type",
        choices=["personal", "full", "work", "project", "devices", "recent"],
        default="personal",
    )
    cli_sync = cli_commands.add_parser("sync", help="update every installed CLI context")
    cli_sync.add_argument("--tool", choices=list(CLI_TOOLS))
    cli_watch = cli_commands.add_parser("watch", help="continuously update installed contexts")
    cli_watch.add_argument("--interval", type=int, default=60)

    daemon_parser = subparsers.add_parser(
        "daemon", help="keep the local API available after user login"
    )
    daemon_commands = daemon_parser.add_subparsers(dest="daemon_command", required=True)
    daemon_install = daemon_commands.add_parser("install", help="install and start a user service")
    daemon_install.add_argument("--host", default="127.0.0.1")
    daemon_install.add_argument("--port", type=int, default=8787)
    daemon_commands.add_parser("status", help="show user-service installation status")
    daemon_commands.add_parser("uninstall", help="stop and remove the user service")
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
        if args.command == "link":
            if args.host not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("The link service may only bind to a loopback host")
            item = VaultRepository(args.vault).create_link_code(args.ttl)
            print(f"Extension link code: {item['code']}", flush=True)
            print(f"Expires in {args.ttl // 60} minutes and can be used once.", flush=True)
            if args.code_only:
                return 0
            print("Keep this process running while the extension is connected.", flush=True)
            serve(args.vault, args.host, args.port)
            return 0
        if args.command == "import":
            pipeline = ImportPipeline(VaultRepository(args.vault))
            standalone = args.format == "browser-vault"
            if args.format == "auto" and args.source.suffix.lower() == ".json":
                try:
                    header = json.loads(args.source.read_text(encoding="utf-8"))
                    standalone = isinstance(header, dict) and header.get("schema") == 1 and isinstance(header.get("claims"), list)
                except (OSError, json.JSONDecodeError):
                    standalone = False
            if standalone:
                result = pipeline.import_standalone_vault(args.source, space=args.space)
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                result = pipeline.import_chatgpt(
                    args.source,
                    account_id=args.account,
                    space=args.space,
                    extract=not args.no_extract,
                )
                print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
            return 0
        if args.command == "imports":
            print(json.dumps(VaultRepository(args.vault).list_imports(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "devices":
            repository = VaultRepository(args.vault)
            if args.device_command == "scan":
                print(json.dumps(repository.upsert_device_scan(scan_device(args.name)), ensure_ascii=False, indent=2))
            else:
                print(json.dumps(repository.list_devices(), ensure_ascii=False, indent=2))
            return 0
        if args.command in {"routes", "sync", "privacy"}:
            sync_service = SyncService(VaultRepository(args.vault))
            if args.command == "routes":
                if args.route_command == "add":
                    policy = {
                        "allowed_categories": [item.strip() for item in args.categories.split(",") if item.strip()],
                        "max_sensitivity": args.max_sensitivity,
                        "sensitive_mode": args.sensitive,
                        "summary_budget_chars": args.budget,
                        "attachment_mode": args.attachments,
                    }
                    result = sync_service.add_route(
                        source_account_id=args.source_account,
                        space=args.space,
                        target_account_id=args.target_account,
                        policy=policy,
                    )
                elif args.route_command == "preview":
                    result = asdict(sync_service.preview(args.route_id, args.approve_sensitive))
                elif args.route_command == "disable":
                    sync_service.disable_route(args.route_id)
                    result = {"route_id": args.route_id, "enabled": False}
                elif args.route_command == "automation":
                    result = sync_service.configure_automation(
                        args.route_id,
                        enabled=args.mode == "full",
                        interval_minutes=args.interval,
                        risk_acknowledged=args.acknowledge_data_risk,
                    )
                else:
                    result = sync_service.list_routes()
            elif args.command == "sync":
                if args.sync_command == "run":
                    result = sync_service.run(args.route_id, args.approve_sensitive)
                    if args.output:
                        args.output.expanduser().resolve().write_text(
                            result["content"], encoding="utf-8"
                        )
                        result["output"] = str(args.output)
                elif args.sync_command == "acknowledge":
                    result = sync_service.acknowledge(args.receipt_id)
                else:
                    result = sync_service.list_receipts()
            elif args.privacy_command == "enable-sensitive":
                sync_service.set_sensitive_sync(True)
                result = {"sensitive_sync_enabled": True}
            elif args.privacy_command == "disable-sensitive":
                sync_service.set_sensitive_sync(False)
                result = {"sensitive_sync_enabled": False}
            elif args.privacy_command == "revoke":
                sync_service.revoke_consent(args.consent_id)
                result = {"consent_id": args.consent_id, "revoked": True}
            else:
                result = {
                    "consent_id": sync_service.record_consent(
                        args.route_id,
                        [item.strip() for item in args.categories.split(",") if item.strip()],
                        args.mode,
                    )
                }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "summary":
            result = SummaryEngineService(VaultRepository(args.vault)).generate(
                engine=args.engine,
                summary_type=args.type,
                space=args.space,
                model=args.model,
                base_url=args.base_url,
                api_key_env=args.api_key_env,
                allow_cloud=args.allow_cloud,
                max_chars=args.max_chars,
            )
            print(result["content"])
            return 0
        if args.command == "models":
            print(json.dumps(SummaryEngineService(VaultRepository(args.vault)).detect(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "captures":
            service = CaptureService(VaultRepository(args.vault))
            if args.capture_command == "list":
                result = service.list()
            elif args.capture_command == "enable":
                result = service.configure(
                    args.account_id,
                    enabled=True,
                    interval_minutes=args.interval,
                    risk_acknowledged=args.acknowledge_privacy_risk,
                    conversation_url=args.conversation_url,
                )
            else:
                result = service.configure(args.account_id, enabled=False)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "extension":
            repository = VaultRepository(args.vault)
            token = (
                repository.rotate_extension_pairing_token()
                if args.extension_command == "rotate-token"
                else repository.extension_pairing_token()
            )
            print(token)
            return 0
        if args.command == "providers":
            print(json.dumps(provider_capabilities(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "cli":
            service = CliAdapterService(VaultRepository(args.vault))
            if args.cli_command == "list":
                result = service.tools()
            elif args.cli_command == "status":
                result = service.installations()
            elif args.cli_command == "install":
                result = service.install(
                    args.tool,
                    scope=args.scope,
                    directory=args.directory,
                    space=args.space,
                    summary_type=args.summary_type,
                )
            elif args.cli_command == "sync":
                result = service.sync(args.tool)
            else:
                print("Watching ContextVault profile changes. Press Ctrl-C to stop.")
                try:
                    service.watch(args.interval)
                except KeyboardInterrupt:
                    print("Stopped.")
                return 0
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "daemon":
            if args.daemon_command == "install":
                result = install_daemon(
                    args.vault, host=args.host, port=args.port
                )
            elif args.daemon_command == "uninstall":
                result = uninstall_daemon()
            else:
                result = daemon_status()
            print(json.dumps(result, ensure_ascii=False, indent=2))
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
                if args.account_command == "rename":
                    account = repository.update_account(args.account_id, label=args.label)
                    print(f"Renamed account: {account.id} ({account.account_label})")
                    return 0
                if args.account_command in {"disconnect", "revoke"}:
                    account = repository.update_account(
                        args.account_id,
                        status={"disconnect": "disconnected", "revoke": "revoked"}[
                            args.account_command
                        ],
                    )
                    print(f"Updated account: {account.id} ({account.status})")
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
                if args.claim_command == "confirm-all":
                    claims = service.confirm_all(args.space)
                    print(f"Confirmed claims: {len(claims)}")
                    return 0
                if args.claim_command == "delete":
                    repository.delete_claim(args.claim_id)
                    print(f"Deleted claim: {args.claim_id}")
                    return 0
                if args.claim_command == "search":
                    claims = repository.search_claims(args.query)
                    print(json.dumps([claim_to_dict(claim) for claim in claims], ensure_ascii=False, indent=2))
                    return 0
                selected_status = ClaimStatus(args.status) if args.status else None
                claims = repository.list_claims(status=selected_status, space=args.space)
                print(json.dumps([claim_to_dict(claim) for claim in claims], ensure_ascii=False, indent=2))
                return 0
            if args.command == "profile":
                if args.profile_command == "health":
                    print(json.dumps(service.health(args.space), ensure_ascii=False, indent=2))
                    return 0
                if args.profile_command == "export-browser":
                    payload = browser_vault_payload(repository, args.space)
                    args.output.expanduser().resolve().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"Exported browser vault: {args.output}")
                    return 0
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
