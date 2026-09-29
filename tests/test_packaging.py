#!/usr/bin/env python3
"""Source + zip layout for the double-click Mac and Windows packs."""
from __future__ import annotations

import stat
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = (root / "VERSION").read_text(encoding="utf-8").strip()
assert version == "0.3.1", version


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

mac_zip = root / f"ClassInterpreter-mac-{version}.zip"
assert mac_zip.is_file(), f"rebuild {mac_zip.name}"
assert (root / "ClassInterpreter-mac.zip").is_file()
with zipfile.ZipFile(mac_zip) as zf:
    names = zf.namelist()
    prefix = f"ClassInterpreter-mac-{version}/"
    assert any(name.endswith("Open.command") for name in names), names
    assert any(name.startswith(prefix) for name in names), names
    assert any("听课搭子.app/Contents/MacOS/launcher" in name for name in names)
    assert any(name.endswith("PkgInfo") for name in names)
    for info in zf.infolist():
        if info.filename.endswith(("Open.command", "Contents/MacOS/launcher", "bootstrap.sh")):
            mode = unix_mode(info)
            assert mode & stat.S_IXUSR, f"{info.filename} not executable: {oct(mode)}"
            data = zf.read(info)
            if info.filename.endswith("Open.command"):
                assert b"launcher" in data

    assert any("deepseek_api.py" in name for name in names)
    assert any(name.endswith("deepseek_api.enc") for name in names)
    assert not any(name.endswith("deepseek.api") for name in names)
    for name in names:
        if name.endswith("deepseek_api.enc"):
            payload = zf.read(name)
            assert payload.startswith(b"CI1.")
            assert b"sk-" not in payload

inner = f"ClassInterpreter-{version}"
win_zip = root / f"ClassInterpreter-windows-{version}.zip"
assert win_zip.is_file(), f"rebuild {win_zip.name}"
assert (root / "ClassInterpreter-windows.zip").is_file()
with zipfile.ZipFile(win_zip) as zf:
    names = zf.namelist()
    assert "READ-ME-FIRST.txt" in names, names
    assert f"{inner}/Start.bat" in names, names
    assert f"{inner}/start.ps1" in names
    assert f"{inner}/HOW-TO-START.txt" in names
    readme = zf.read("READ-ME-FIRST.txt")
    assert all(byte < 128 for byte in readme)
    assert b"0.3.1" in readme
    assert b"0.2.5" in readme
    start_ps1 = zf.read(f"{inner}/start.ps1")
    assert start_ps1.startswith(b"\xef\xbb\xbf")
    assert all(byte < 128 for byte in start_ps1[3:])
    assert b"Downloading official Python" in start_ps1
    start_bat = zf.read(f"{inner}/Start.bat")
    assert all(byte < 128 for byte in start_bat)
    assert b"ExecutionPolicy Bypass" in start_bat
    assert b"0.3.1" in start_bat
    got = zf.read(f"{inner}/VERSION").decode().strip()
    assert got == version, got
    assert f"{inner}/secret_box.py" in names
    assert f"{inner}/deepseek_api.py" in names
    assert f"{inner}/deepseek_api.enc" in names
    enc = zf.read(f"{inner}/deepseek_api.enc")
    assert enc.startswith(b"CI1.")
    assert b"sk-" not in enc
    assert not any(name.endswith("secrets/deepseek.api") or name.endswith("/deepseek.api") for name in names)

print("packaging ok")
