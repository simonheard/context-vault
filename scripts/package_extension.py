from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


def package_extension(source: Path, output: Path) -> Path:
    source = source.resolve()
    manifest = source / "manifest.json"
    if not manifest.is_file():
        raise ValueError(f"Extension manifest not found: {manifest}")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if payload.get("manifest_version") != 3:
        raise ValueError("Only a Chrome Manifest V3 extension can be packaged")
    files = sorted(
        path for path in source.rglob("*") if path.is_file() and not path.name.startswith(".")
    )
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo.from_file(path, path.relative_to(source).as_posix())
            info.date_time = (2026, 1, 1, 0, 0, 0)
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the ContextVault Chrome extension ZIP")
    parser.add_argument("--source", type=Path, default=Path("extension"))
    parser.add_argument(
        "--output", type=Path, default=Path("dist/contextvault-extension.zip")
    )
    args = parser.parse_args()
    print(package_extension(args.source, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
