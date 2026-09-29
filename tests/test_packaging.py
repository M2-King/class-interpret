#!/usr/bin/env python3
"""Source + zip layout for the double-click Mac and Windows packs."""
from __future__ import annotations

import stat
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]


def unix_mode(info: zipfile.ZipInfo) -> int:
    return (info.external_attr >> 16) & 0xFFFF


open_cmd = root / "packaging/macos/Open.command"
assert open_cmd.is_file()
text = open_cmd.read_text(encoding="utf-8")
assert text.startswith("#!/bin/bash")
assert "Contents/MacOS/launcher" in text
assert "xattr" in text

pkginfo = root / "听课搭子.app/Contents/PkgInfo"
assert pkginfo.read_bytes() == b"APPL????"

mac_zip = root / "ClassInterpreter-mac.zip"
assert mac_zip.is_file(), "rebuild ClassInterpreter-mac.zip"
with zipfile.ZipFile(mac_zip) as zf:
    names = zf.namelist()
    assert any(name.endswith("Open.command") for name in names), names
    assert any("听课搭子.app/Contents/MacOS/launcher" in name for name in names)
    assert any(name.endswith("PkgInfo") for name in names)
    for info in zf.infolist():
        if info.filename.endswith(("Open.command", "Contents/MacOS/launcher", "bootstrap.sh")):
            mode = unix_mode(info)
            assert mode & stat.S_IXUSR, f"{info.filename} not executable: {oct(mode)}"
            data = zf.read(info)
            if info.filename.endswith("Open.command"):
                assert b"launcher" in data

win_zip = root / "ClassInterpreter-windows.zip"
assert win_zip.is_file(), "rebuild ClassInterpreter-windows.zip"
with zipfile.ZipFile(win_zip) as zf:
    names = zf.namelist()
    assert "ClassInterpreter/Start.bat" in names, names
    assert "ClassInterpreter/start.ps1" in names
    assert "ClassInterpreter/HOW-TO-START.txt" in names
    start_ps1 = zf.read("ClassInterpreter/start.ps1")
    assert start_ps1.startswith(b"\xef\xbb\xbf")
    assert all(byte < 128 for byte in start_ps1[3:])
    start_bat = zf.read("ClassInterpreter/Start.bat")
    assert all(byte < 128 for byte in start_bat)
    assert b"ExecutionPolicy Bypass" in start_bat
    version = zf.read("ClassInterpreter/VERSION").decode().strip()
    assert version == "0.2.6", version

print("packaging ok")
