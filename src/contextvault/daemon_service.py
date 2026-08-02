from __future__ import annotations

import os
import platform
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Optional


LABEL = "com.contextvault.server"


def daemon_status(home: Optional[Path] = None) -> dict[str, object]:
    system = platform.system()
    path = _definition_path(system, home or Path.home())
    return {"platform": system, "installed": path.exists(), "path": str(path)}


def install_daemon(
    vault: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8787,
    home: Optional[Path] = None,
    activate: bool = True,
) -> dict[str, object]:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("The background service may only bind to loopback")
    if not 1 <= port <= 65535:
        raise ValueError("Invalid service port")
    system = platform.system()
    user_home = (home or Path.home()).expanduser().resolve()
    path = _definition_path(system, user_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "contextvault",
        "--vault",
        str(vault.expanduser().resolve()),
        "ui",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if system == "Darwin":
        payload = {
            "Label": LABEL,
            "ProgramArguments": command,
            "RunAtLoad": True,
            "KeepAlive": True,
            "StandardOutPath": str(user_home / "Library/Logs/contextvault.log"),
            "StandardErrorPath": str(user_home / "Library/Logs/contextvault.error.log"),
        }
        path.write_bytes(plistlib.dumps(payload, sort_keys=True))
        if activate:
            domain = f"gui/{os.getuid()}"
            subprocess.run(["launchctl", "bootout", domain, str(path)], check=False, capture_output=True)
            result = subprocess.run(
                ["launchctl", "bootstrap", domain, str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise OSError(result.stderr.strip() or "launchctl bootstrap failed")
    elif system == "Linux":
        escaped = " ".join(_systemd_escape(item) for item in command)
        path.write_text(
            "[Unit]\nDescription=ContextVault local service\n\n"
            "[Service]\nType=simple\nRestart=on-failure\n"
            f"ExecStart={escaped}\n\n"
            "[Install]\nWantedBy=default.target\n",
            encoding="utf-8",
        )
        if activate:
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
            subprocess.run(
                ["systemctl", "--user", "enable", "--now", "contextvault.service"],
                check=True,
            )
    elif system == "Windows":
        path.write_text("@echo off\r\n" + subprocess.list2cmdline(command) + "\r\n", encoding="utf-8")
        if activate:
            subprocess.run(
                [
                    "schtasks",
                    "/Create",
                    "/F",
                    "/SC",
                    "ONLOGON",
                    "/TN",
                    "ContextVault",
                    "/TR",
                    str(path),
                ],
                check=True,
            )
    else:
        raise ValueError(f"Unsupported daemon platform: {system}")
    return {**daemon_status(user_home), "active_requested": activate, "command": command}


def uninstall_daemon(home: Optional[Path] = None, deactivate: bool = True) -> dict[str, object]:
    system = platform.system()
    user_home = (home or Path.home()).expanduser().resolve()
    path = _definition_path(system, user_home)
    if deactivate and path.exists():
        if system == "Darwin":
            subprocess.run(
                ["launchctl", "bootout", f"gui/{os.getuid()}", str(path)],
                check=False,
                capture_output=True,
            )
        elif system == "Linux":
            subprocess.run(
                ["systemctl", "--user", "disable", "--now", "contextvault.service"],
                check=False,
            )
        elif system == "Windows":
            subprocess.run(
                ["schtasks", "/Delete", "/F", "/TN", "ContextVault"],
                check=False,
            )
    if path.exists():
        path.unlink()
    return {"platform": system, "installed": False, "path": str(path)}


def _definition_path(system: str, home: Path) -> Path:
    if system == "Darwin":
        return home / "Library/LaunchAgents" / f"{LABEL}.plist"
    if system == "Linux":
        return home / ".config/systemd/user/contextvault.service"
    if system == "Windows":
        return home / "AppData/Roaming/ContextVault/contextvault-start.cmd"
    raise ValueError(f"Unsupported daemon platform: {system}")


def _systemd_escape(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"
