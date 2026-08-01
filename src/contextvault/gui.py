from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from contextvault.vault import initialize


STATIC_TYPES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


def dashboard_snapshot(path: Path) -> dict[str, Any]:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        counts = {
            "claims": _count(connection, "claims"),
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
    platform = platform.strip().lower()
    label = label.strip()
    if platform not in {"chatgpt", "gemini", "claude", "other"}:
        raise ValueError("Unsupported provider")
    if not 1 <= len(label) <= 80:
        raise ValueError("Account label must be between 1 and 80 characters")
    now = datetime.now(timezone.utc).isoformat()
    account = {
        "id": f"account_{uuid4().hex}",
        "platform": platform,
        "account_label": label,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO provider_accounts(
                id, platform, account_label, status, created_at, updated_at
            ) VALUES (:id, :platform, :account_label, :status, :created_at, :updated_at)
            """,
            account,
        )
    return account


def create_profile_space(path: Path, name: str, display_name: str) -> dict[str, Any]:
    name = name.strip().lower().replace(" ", "-")
    display_name = display_name.strip()
    if not name or not all(character.isalnum() or character in "-_" for character in name):
        raise ValueError("Space name may contain letters, numbers, hyphens, and underscores")
    if not 1 <= len(display_name) <= 80:
        raise ValueError("Display name must be between 1 and 80 characters")
    now = datetime.now(timezone.utc).isoformat()
    space = {
        "id": f"space_{uuid4().hex}",
        "name": name,
        "display_name": display_name,
        "is_default": 0,
        "created_at": now,
        "updated_at": now,
    }
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO profile_spaces(
                id, name, display_name, is_default, created_at, updated_at
            ) VALUES (:id, :name, :display_name, :is_default, :created_at, :updated_at)
            """,
            space,
        )
    return space


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
        def do_GET(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
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
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
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
            self.end_headers()
            self.wfile.write(payload)

    return Handler


def _count(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

