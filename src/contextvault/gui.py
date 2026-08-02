from __future__ import annotations

import json
import hmac
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from contextvault.domain import Sensitivity, SourceType
from contextvault.repository import VaultRepository
from contextvault.services import ProfileService, claim_to_dict
from contextvault.vault import initialize
from contextvault.device_agent import scan_device
from contextvault.pipeline import ImportPipeline
from contextvault.sync_service import SyncService
from contextvault.providers import provider_capabilities
from contextvault.protocol import (
    MIN_PROTOCOL_VERSION,
    PROTOCOL_VERSION,
    check_protocol,
)
from contextvault import __version__
from contextvault.vault import SCHEMA_VERSION


STATIC_TYPES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


def dashboard_snapshot(path: Path) -> dict[str, Any]:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        counts = {
            "claims": connection.execute(
                "SELECT COUNT(*) FROM claims WHERE status = 'confirmed'"
            ).fetchone()[0],
            "candidates": connection.execute(
                "SELECT COUNT(*) FROM claims WHERE status = 'candidate'"
            ).fetchone()[0],
            "sensitive": connection.execute(
                "SELECT COUNT(*) FROM claims WHERE sensitivity = 'sensitive'"
            ).fetchone()[0],
            "devices": _count(connection, "devices"),
            "accounts": _count(connection, "provider_accounts"),
            "spaces": _count(connection, "profile_spaces"),
            "routes": _count(connection, "sync_routes"),
            "receipts": _count(connection, "sync_receipts"),
            "attachments": _count(connection, "attachment_refs"),
            "events": _count(connection, "sync_events"),
        }
    return {"counts": counts}


def list_rows(path: Path, table: str) -> list[dict[str, Any]]:
    allowed = {"provider_accounts", "profile_spaces"}
    if table not in allowed:
        raise ValueError("Unsupported table")
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {table} ORDER BY created_at").fetchall()
    return [dict(row) for row in rows]


def create_provider_account(path: Path, platform: str, label: str) -> dict[str, Any]:
    account = VaultRepository(path).add_account(platform, label)
    return {
        "id": account.id,
        "platform": account.platform,
        "account_label": account.account_label,
        "status": account.status,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


def create_profile_space(path: Path, name: str, display_name: str) -> dict[str, Any]:
    space = VaultRepository(path).add_space(name, display_name)
    return {
        "id": space.id,
        "name": space.name,
        "display_name": space.display_name,
        "is_default": int(space.is_default),
        "created_at": space.created_at,
        "updated_at": space.updated_at,
    }


def serve(path: Path, host: str, port: int) -> None:
    vault_path = initialize(path).path
    handler = _handler_for(vault_path)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"ContextVault UI: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _handler_for(vault_path: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_OPTIONS(self) -> None:  # noqa: N802
            if self._extension_origin():
                self.send_response(HTTPStatus.NO_CONTENT)
                self._cors_headers()
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header(
                    "Access-Control-Allow-Headers",
                    "Content-Type, X-ContextVault-Token, X-ContextVault-Protocol",
                )
                self.send_header("Access-Control-Allow-Private-Network", "true")
                self.end_headers()
                return
            self._json({"error": "Origin not allowed"}, HTTPStatus.FORBIDDEN)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            route = parsed.path
            if route.startswith("/api/") and not self._authorized():
                self._json({"error": "Extension pairing token is invalid"}, HTTPStatus.FORBIDDEN)
                return
            if not self._protocol_allowed(route):
                self._protocol_error()
                return
            if route in STATIC_TYPES:
                filename, content_type = STATIC_TYPES[route]
                payload = files("contextvault").joinpath("web", filename).read_bytes()
                self._send(payload, content_type)
                return
            if route == "/api/dashboard":
                self._json(dashboard_snapshot(vault_path))
                return
            if route == "/api/accounts":
                self._json({"items": list_rows(vault_path, "provider_accounts")})
                return
            if route == "/api/spaces":
                self._json({"items": list_rows(vault_path, "profile_spaces")})
                return
            repository = VaultRepository(vault_path)
            service = ProfileService(repository)
            if route == "/api/claims":
                self._json(
                    {"items": [claim_to_dict(item) for item in repository.list_claims()]}
                )
                return
            if route == "/api/profile":
                self._json(service.current_profile("personal"))
                return
            if route == "/api/profile/health":
                self._json(service.health("personal"))
                return
            if route == "/api/events":
                self._json(
                    {
                        "items": [
                            {
                                "sequence": event.sequence,
                                "event_type": event.event_type,
                                "aggregate_type": event.aggregate_type,
                                "aggregate_id": event.aggregate_id,
                                "created_at": event.created_at,
                            }
                            for event in repository.list_events()
                        ]
                    }
                )
                return
            if route == "/api/devices":
                self._json({"items": repository.list_devices()})
                return
            if route == "/api/imports":
                self._json({"items": repository.list_imports()})
                return
            sync_service = SyncService(repository)
            if route == "/api/routes":
                self._json({"items": sync_service.list_routes()})
                return
            if route == "/api/receipts":
                self._json({"items": sync_service.list_receipts()})
                return
            if route == "/api/privacy":
                with repository.transaction() as connection:
                    row = connection.execute(
                        "SELECT value FROM metadata WHERE key = 'sensitive_sync_enabled'"
                    ).fetchone()
                self._json({"sensitive_sync_enabled": bool(row and row[0] == "1")})
                return
            if route == "/api/providers":
                self._json({"items": provider_capabilities()})
                return
            if route == "/api/version":
                self._json(
                    {
                        "server_version": __version__,
                        "schema_version": SCHEMA_VERSION,
                        "protocol_version": PROTOCOL_VERSION,
                        "minimum_protocol_version": MIN_PROTOCOL_VERSION,
                    }
                )
                return
            if route == "/api/automation/jobs":
                self._json({"items": SyncService(repository).automation_jobs()})
                return
            if route == "/api/extension/pairing":
                self._json({"token": repository.extension_pairing_token()})
                return
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
            if route.startswith("/api/") and not self._authorized():
                self._json({"error": "Extension pairing token is invalid"}, HTTPStatus.FORBIDDEN)
                return
            if not self._protocol_allowed(route):
                self._protocol_error()
                return
            try:
                body = self._read_json()
                if route == "/api/accounts":
                    item = create_provider_account(
                        vault_path, str(body.get("platform", "")), str(body.get("label", ""))
                    )
                    self._json({"item": item}, HTTPStatus.CREATED)
                    return
                if route == "/api/spaces":
                    item = create_profile_space(
                        vault_path, str(body.get("name", "")), str(body.get("display_name", ""))
                    )
                    self._json({"item": item}, HTTPStatus.CREATED)
                    return
                repository = VaultRepository(vault_path)
                service = ProfileService(repository)
                if route == "/api/claims":
                    claim = service.add_candidate(
                        attribute=str(body.get("attribute", "")),
                        value=body.get("value", ""),
                        space=str(body.get("space", "personal")),
                        confidence=float(body.get("confidence", 1.0)),
                        sensitivity=Sensitivity(str(body.get("sensitivity", "personal"))),
                        source_type=SourceType.MANUAL,
                    )
                    self._json({"item": claim_to_dict(claim)}, HTTPStatus.CREATED)
                    return
                if route == "/api/claims/confirm-all":
                    items = [claim_to_dict(item) for item in service.confirm_all()]
                    self._json({"items": items})
                    return
                if route == "/api/imports":
                    result = ImportPipeline(repository).import_chatgpt(
                        Path(str(body.get("path", ""))),
                        account_id=(str(body["account_id"]) if body.get("account_id") else None),
                        space=str(body.get("space", "personal")),
                    )
                    self._json({"item": result.__dict__}, HTTPStatus.CREATED)
                    return
                if route == "/api/devices/scan":
                    item = repository.upsert_device_scan(
                        scan_device(str(body["name"]) if body.get("name") else None)
                    )
                    self._json({"item": item}, HTTPStatus.CREATED)
                    return
                sync_service = SyncService(repository)
                if route == "/api/routes":
                    if (
                        str(body.get("automation_mode", "manual")) == "full"
                        and not body.get("risk_acknowledged")
                    ):
                        raise ValueError(
                            "Full automation requires explicit data-risk acknowledgement"
                        )
                    item = sync_service.add_route(
                        source_account_id=(
                            str(body["source_account_id"])
                            if body.get("source_account_id")
                            else None
                        ),
                        space=str(body.get("space", "personal")),
                        target_account_id=str(body.get("target_account_id", "")),
                        policy={
                            "allowed_categories": [
                                item.strip()
                                for item in str(body.get("categories", "*")).split(",")
                                if item.strip()
                            ],
                            "max_sensitivity": str(
                                body.get("max_sensitivity", "personal")
                            ),
                            "sensitive_mode": str(body.get("sensitive_mode", "block")),
                            "attachment_mode": str(
                                body.get("attachment_mode", "reference")
                            ),
                        },
                    )
                    if str(body.get("automation_mode", "manual")) == "full":
                        sync_service.configure_automation(
                            str(item["id"]),
                            enabled=True,
                            interval_minutes=int(
                                body.get("automation_interval_minutes", 60)
                            ),
                            risk_acknowledged=bool(body.get("risk_acknowledged")),
                        )
                    self._json({"item": item}, HTTPStatus.CREATED)
                    return
                if route in {"/api/privacy/enable", "/api/privacy/disable"}:
                    enabled = route.endswith("enable")
                    sync_service.set_sensitive_sync(enabled)
                    self._json({"sensitive_sync_enabled": enabled})
                    return
                if route == "/api/clients/register":
                    item = repository.register_client(
                        str(body.get("id", "")),
                        str(body.get("client_type", "extension")),
                        str(body.get("client_version", "unknown")),
                        int(body.get("protocol_version", 1)),
                    )
                    self._json({"item": item}, HTTPStatus.CREATED)
                    return
                route_parts = route.strip("/").split("/")
                if len(route_parts) == 4 and route_parts[:2] == ["api", "claims"]:
                    claim_id, action = route_parts[2], route_parts[3]
                    if action == "confirm":
                        self._json({"item": claim_to_dict(service.confirm(claim_id))})
                        return
                    if action == "reject":
                        self._json({"item": claim_to_dict(service.reject(claim_id))})
                        return
                if len(route_parts) == 4 and route_parts[:2] == ["api", "routes"]:
                    route_id, action = route_parts[2], route_parts[3]
                    approved = bool(body.get("approve_sensitive", False))
                    if action == "preview":
                        self._json({"item": SyncService(repository).preview(route_id, approved).__dict__})
                        return
                    if action == "sync":
                        self._json({"item": SyncService(repository).run(route_id, approved)})
                        return
                    if action == "automation":
                        self._json(
                            {
                                "item": SyncService(repository).configure_automation(
                                    route_id,
                                    enabled=bool(body.get("enabled", False)),
                                    interval_minutes=int(body.get("interval_minutes", 60)),
                                    risk_acknowledged=bool(
                                        body.get("risk_acknowledged", False)
                                    ),
                                )
                            }
                        )
                        return
                    if action == "automate":
                        self._json(
                            {"item": SyncService(repository).run_automation(route_id)}
                        )
                        return
                if len(route_parts) == 4 and route_parts[:2] == ["api", "receipts"]:
                    receipt_id, action = route_parts[2], route_parts[3]
                    if action == "acknowledge":
                        self._json(
                            {"item": SyncService(repository).acknowledge(receipt_id)}
                        )
                        return
                    if action == "fail":
                        self._json(
                            {
                                "item": SyncService(repository).fail_receipt(
                                    receipt_id, str(body.get("reason", "adapter_failed"))
                                )
                            }
                        )
                        return
                self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            except (ValueError, sqlite3.IntegrityError) as error:
                self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 64_000:
                raise ValueError("Request body is too large")
            payload = self.rfile.read(length)
            value = json.loads(payload or b"{}")
            if not isinstance(value, dict):
                raise ValueError("JSON body must be an object")
            return value

        def _json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            self._send(
                json.dumps(value, ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8",
                status,
            )

        def _send(
            self,
            payload: bytes,
            content_type: str,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'")
            self.send_header("X-ContextVault-Protocol", str(PROTOCOL_VERSION))
            self._cors_headers()
            self.end_headers()
            self.wfile.write(payload)

        def _extension_origin(self) -> str | None:
            origin = self.headers.get("Origin", "")
            return origin if origin.startswith("chrome-extension://") else None

        def _authorized(self) -> bool:
            if not self._extension_origin():
                return True
            supplied = self.headers.get("X-ContextVault-Token", "")
            expected = VaultRepository(vault_path).extension_pairing_token()
            return extension_request_authorized(
                self._extension_origin(), supplied, expected
            )

        def _cors_headers(self) -> None:
            origin = self._extension_origin()
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")

        def _protocol_allowed(self, route: str) -> bool:
            if not self._extension_origin() or route == "/api/version":
                return True
            try:
                version = int(self.headers.get("X-ContextVault-Protocol", "1"))
            except ValueError:
                return False
            return check_protocol(version).compatible

        def _protocol_error(self) -> None:
            self._json(
                {
                    "error": "Client/server protocol versions are incompatible",
                    "server_protocol": PROTOCOL_VERSION,
                    "minimum_protocol": MIN_PROTOCOL_VERSION,
                },
                HTTPStatus.UPGRADE_REQUIRED,
            )

    return Handler


def _count(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def extension_request_authorized(
    origin: str | None, supplied_token: str, expected_token: str
) -> bool:
    if not origin:
        return True
    if not origin.startswith("chrome-extension://"):
        return False
    return bool(supplied_token) and hmac.compare_digest(supplied_token, expected_token)
