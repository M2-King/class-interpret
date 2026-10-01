#!/usr/bin/env python3
"""Copy versioned install zips to stable docs/ names and stamp the intro site.

Download URLs stay ClassInterpreter-mac.zip / ClassInterpreter-windows.zip
across versions. GitHub Release /releases/latest/download/ uses the same names.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

MAC = "ClassInterpreter-mac.zip"
WIN = "ClassInterpreter-windows.zip"
DEFAULT_REPO = "M2-King/class-interpret"
# Three-part versions such as 0.3.3, not 127.0.0.1 or 1.5.
_VERSION_RE = re.compile(r"(?<!\d\.)(?<!\d)\d+\.\d+\.\d+(?!\.\d)")


def version_of(root: Path) -> str:
    text = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"empty VERSION in {root}")
    return text


def release_base(repo: str | None = None) -> str:
    name = repo or os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO
    return f"https://github.com/{name}/releases/latest/download"


def rewrite_zip_hrefs(html: str) -> str:
    html = re.sub(
        r"ClassInterpreter-mac-\d+\.\d+\.\d+\.zip",
        MAC,
        html,
    )
    html = re.sub(
        r"ClassInterpreter-windows-\d+\.\d+\.\d+\.zip",
        WIN,
        html,
    )
    return html


def stamp_versions(text: str, version: str) -> str:
    return _VERSION_RE.sub(version, text)


def copy_pack(root: Path, docs: Path, kind: str, version: str) -> None:
    src = root / f"ClassInterpreter-{kind}-{version}.zip"
    if not src.is_file():
        raise FileNotFoundError(f"missing {src.name}; build the pack first")
    stable = docs / f"ClassInterpreter-{kind}.zip"
    versioned = docs / f"ClassInterpreter-{kind}-{version}.zip"
    shutil.copyfile(src, stable)
    shutil.copyfile(src, versioned)


def latest_payload(version: str, repo: str | None = None) -> dict[str, str]:
    base = release_base(repo)
    return {
        "version": version,
        "mac": MAC,
        "windows": WIN,
        "github_mac": f"{base}/{MAC}",
        "github_windows": f"{base}/{WIN}",
    }


def publish(root: Path, repo: str | None = None) -> None:
    root = Path(root)
    version = version_of(root)
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    copy_pack(root, docs, "mac", version)
    copy_pack(root, docs, "windows", version)
    html_path = docs / "index.html"
    if html_path.is_file():
        html = rewrite_zip_hrefs(html_path.read_text(encoding="utf-8"))
        html_path.write_text(stamp_versions(html, version), encoding="utf-8")
    payload = latest_payload(version, repo)
    (docs / "latest.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    publish(root)
    version = version_of(root)
    print(f"published {version} -> docs/{MAC} docs/{WIN} docs/latest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
