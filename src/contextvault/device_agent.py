from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional


_TOOLS = {
    "python": ["python3", "--version"],
    "node": ["node", "--version"],
    "git": ["git", "--version"],
    "docker": ["docker", "--version"],
    "podman": ["podman", "--version"],
    "ruby": ["ruby", "--version"],
    "go": ["go", "version"],
    "rust": ["rustc", "--version"],
    "java": ["java", "-version"],
}


def scan_device(display_name: Optional[str] = None) -> dict[str, object]:
    system = platform.system() or "Unknown"
    machine = platform.machine() or "Unknown"
    release = platform.release() or "Unknown"
    model = _device_model(system)
    memory = _memory_bytes(system)
    tools = {name: version for name, command in _TOOLS.items() if (version := _version(command))}
    stable = json.dumps(
        {"system": system, "machine": machine, "model": model}, sort_keys=True
    )
    fingerprint = hashlib.sha256(stable.encode()).hexdigest()
    return {
        "display_name": display_name or f"{model} ({system})",
        "device_type": "computer",
        "fingerprint": fingerprint,
        "config": {
            "model": model,
            "os": system,
            "os_release": release,
            "architecture": machine,
            "cpu": platform.processor() or machine,
            "memory_bytes": memory,
            "tools": tools,
        },
    }


def _version(command: list[str]) -> Optional[str]:
    if shutil.which(command[0]) is None:
        return None
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0][:160] if output else None


def _device_model(system: str) -> str:
    if system == "Darwin":
        value = _version(["sysctl", "-n", "hw.model"])
        return value or "Mac"
    model_path = Path("/sys/devices/virtual/dmi/id/product_name")
    if model_path.is_file():
        try:
            return model_path.read_text().strip()[:100] or "Computer"
        except OSError:
            pass
    return platform.node() or "Computer"


def _memory_bytes(system: str) -> Optional[int]:
    if system == "Darwin":
        value = _version(["sysctl", "-n", "hw.memsize"])
        try:
            return int(value) if value else None
        except ValueError:
            return None
    memory_path = Path("/proc/meminfo")
    if memory_path.is_file():
        try:
            first = memory_path.read_text().splitlines()[0].split()[1]
            return int(first) * 1024
        except (OSError, IndexError, ValueError):
            return None
    return None
