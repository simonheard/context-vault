from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def verify(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"CLI wheel not found: {path}")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
    if not any(name.endswith("contextvault/cli.py") for name in names):
        raise ValueError("Wheel does not contain the ContextVault CLI")
    if any(name.startswith("extension/") or "/extension/" in name for name in names):
        raise ValueError("Independent CLI wheel must not contain the browser extension")
    entry_points = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
    if len(entry_points) != 1:
        raise ValueError("Wheel must contain one entry-point manifest")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    verify(args.wheel)
    print(f"verified independent CLI wheel: {args.wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
