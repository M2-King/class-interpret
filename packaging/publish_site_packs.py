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


def pack_names(version: str) -> dict[str, str]:
    return {
        "version": version,
        "tag": f"v{version}",
        "mac": MAC,
        "windows": WIN,
        "mac_versioned": f"ClassInterpreter-mac-{version}.zip",
        "windows_versioned": f"ClassInterpreter-windows-{version}.zip",
        "mac_folder": f"ClassInterpreter-mac-{version}",
        "windows_folder": f"ClassInterpreter-{version}",
        "banner": f"Class Interpreter {version}",
    }


def latest_payload(version: str, repo: str | None = None) -> dict[str, str]:
    name = repo or os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO
    base = release_base(name)
    names = pack_names(version)
    names.update(
        {
            "github_mac": f"{base}/{MAC}",
            "github_windows": f"{base}/{WIN}",
            "github_mac_versioned": f"{base}/{names['mac_versioned']}",
            "github_windows_versioned": f"{base}/{names['windows_versioned']}",
            "api_latest": f"https://api.github.com/repos/{name}/releases/latest",
        }
    )
    return names


def release_body(version: str, repo: str | None = None) -> str:
    names = pack_names(version)
    name = repo or os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO
    base = release_base(name)
    return (
        f"# 听课搭子 {version}\n"
        "\n"
        "GitHub Live Auto-Sync reads this Release. Download the Assets zips, "
        "not the GitHub Source code archive.\n"
        "\n"
        "## Downloads\n"
        "\n"
        f"- Windows: `{names['windows']}` and `{names['windows_versioned']}` (same pack)\n"
        f"- Mac: `{names['mac']}` and `{names['mac_versioned']}` (same pack)\n"
        "\n"
        f"- {base}/{names['windows']}\n"
        f"- {base}/{names['mac']}\n"
        "\n"
        "## Extracted folders\n"
        "\n"
        f"- Windows: `{names['windows_folder']}\\`\n"
        f"- Mac: `{names['mac_folder']}/`\n"
        f"- Black window first line: `{names['banner']}`\n"
        "\n"
        "## Install\n"
        "\n"
        "Windows: Extract All → OPEN-THIS.bat → http://127.0.0.1:8765/\n"
        "Mac: Open.command. Do not use a .exe or .dmg; this project ships zip packs only.\n"
    )


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
    (docs / "release-body.md").write_text(release_body(version, repo), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    publish(root)
    version = version_of(root)
    print(f"published {version} -> docs/{MAC} docs/{WIN} docs/latest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
