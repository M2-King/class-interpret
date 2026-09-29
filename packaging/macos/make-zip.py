#!/usr/bin/env python3
"""Build a Mac zip with Unix executable bits Launch Services can use."""
from __future__ import annotations

import os
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "听课搭子.app"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
PREFIX = f"ClassInterpreter-mac-{VERSION}"
OUT = ROOT / f"ClassInterpreter-mac-{VERSION}.zip"
STABLE = ROOT / "ClassInterpreter-mac.zip"


def unix_attr(path: Path) -> int:
    mode = path.stat().st_mode
    if path.is_dir() or path.suffix == ".command" or path.name in {"launcher", "bootstrap.sh"}:
        mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    return (mode & 0xFFFF) << 16


def add(zf: zipfile.ZipFile, src: Path, arc: str) -> None:
    info = zipfile.ZipInfo.from_file(src, arc)
    info.create_system = 3
    info.external_attr = unix_attr(src)
    if any(ord(ch) > 127 for ch in info.filename):
        info.flag_bits |= 0x800
    if src.is_dir():
        if not info.filename.endswith("/"):
            info.filename += "/"
        info.compress_type = zipfile.ZIP_STORED
        zf.writestr(info, b"")
        return
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, src.read_bytes())


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src, name in (
            (ROOT / "packaging/macos/Open.command", f"{PREFIX}/Open.command"),
            (ROOT / "packaging/macos/使用说明.txt", f"{PREFIX}/使用说明.txt"),
        ):
            os.chmod(src, 0o755 if src.suffix == ".command" else 0o644)
            add(zf, src, name)
        for path in APP.rglob("*"):
            rel = path.relative_to(APP)
            add(zf, path, f"{PREFIX}/听课搭子.app/{rel.as_posix()}")
    STABLE.write_bytes(OUT.read_bytes())
    print(f"Wrote {OUT}")
    print(f"Wrote {STABLE}")


if __name__ == "__main__":
    main()
