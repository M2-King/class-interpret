#!/usr/bin/env python3
"""Source + zip layout for the double-click Mac and Windows packs."""
from __future__ import annotations

import stat
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = (root / "VERSION").read_text(encoding="utf-8").strip()
assert version == "0.3.3", version

windows_setup = root / "ClassInterpreter-Setup-Windows.bat"
assert windows_setup.is_file()
windows_setup_bytes = windows_setup.read_bytes()
assert all(byte < 128 for byte in windows_setup_bytes)
assert b"ClassInterpreter-Setup-Windows.ps1" in windows_setup_bytes
assert b"-WindowStyle Hidden" in windows_setup_bytes
windows_setup_gui = root / "ClassInterpreter-Setup-Windows.ps1"
assert windows_setup_gui.is_file()
gui_bytes = windows_setup_gui.read_bytes()
assert all(byte < 128 for byte in gui_bytes)
assert b"System.Windows.Forms" in gui_bytes
assert b"Downloading application" in gui_bytes
assert b"-NoLaunch" in gui_bytes
assert b"api/status" in gui_bytes
assert b"startup.log" in gui_bytes
assert b"taskkill.exe" in gui_bytes
assert b"Class Interpreter was already ready" in gui_bytes

mac_setup_command = root / "ClassInterpreter-Setup-Mac.command"
assert mac_setup_command.is_file()
assert b"ClassInterpreter-mac-0.3.3.zip" in mac_setup_command.read_bytes()


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
    assert any(name.endswith("INSTALL-OR-REPAIR.command") for name in names), names
    assert any(name.endswith("FIX-CLASS-INTERPRETER.command") for name in names), names
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
        if info.filename.endswith("INSTALL-OR-REPAIR.command"):
            mode = unix_mode(info)
            assert mode & stat.S_IXUSR, f"{info.filename} not executable: {oct(mode)}"
            repair = zf.read(info)
            assert b"Detected installation" in repair
            assert b"venv-broken-" in repair
            assert b"repair-backups" in repair

    assert any("deepseek_api.py" in name for name in names)
    assert any(name.endswith("deepseek_api.enc") for name in names)
    assert not any(name.endswith("deepseek.api") for name in names)
    for name in names:
        if name.endswith("deepseek_api.enc"):
            payload = zf.read(name)
            assert payload.startswith(b"CI1.")
            assert b"sk-" not in payload

mac_setup_zip = root / "ClassInterpreter-Setup-Mac.zip"
assert mac_setup_zip.is_file(), f"rebuild {mac_setup_zip.name}"
with zipfile.ZipFile(mac_setup_zip) as zf:
    info = zf.getinfo("ClassInterpreter-Setup-Mac.command")
    assert unix_mode(info) & stat.S_IXUSR
    assert b"INSTALL-OR-REPAIR.command" in zf.read(info)

inner = f"ClassInterpreter-{version}"
win_zip = root / f"ClassInterpreter-windows-{version}.zip"
assert win_zip.is_file(), f"rebuild {win_zip.name}"
assert (root / "ClassInterpreter-windows.zip").is_file()
with zipfile.ZipFile(win_zip) as zf:
    names = zf.namelist()
    assert "READ-ME-FIRST.txt" in names, names
    assert "INSTALL-OR-REPAIR.bat" in names, names
    assert "repair.ps1" in names, names
    assert "OPEN-THIS.bat" in names, names
    assert f"{inner}/Start.bat" in names, names
    assert f"{inner}/FIX-CLASS-INTERPRETER.bat" in names, names
    assert f"{inner}/fix.ps1" in names, names
    assert f"{inner}/start.ps1" in names
    assert f"{inner}/HOW-TO-START.txt" in names
    readme = zf.read("READ-ME-FIRST.txt")
    assert all(byte < 128 for byte in readme)
    assert b"0.3.3" in readme
    assert b"0.2.5" in readme
    open_this = zf.read("OPEN-THIS.bat")
    assert all(byte < 128 for byte in open_this)
    assert b"Extract All" in open_this
    assert b"0.3.3" in open_this
    installer = zf.read("INSTALL-OR-REPAIR.bat")
    assert all(byte < 128 for byte in installer)
    assert b"repair.ps1" in installer
    assert b"Extract All" in installer
    repair = zf.read("repair.ps1")
    assert all(byte < 128 for byte in repair)
    assert b"Detected installation" in repair
    assert b".venv-broken-" in repair
    assert b".repair-backup" in repair
    assert b"Stop-AppForRepair" in repair
    assert b"Close every Class Interpreter or Python window" in repair
    assert b"$target = [string]$selectedTarget" in repair
    assert b"$target = @($candidates" not in repair
    start_ps1 = zf.read(f"{inner}/start.ps1")
    assert start_ps1.startswith(b"\xef\xbb\xbf")
    assert all(byte < 128 for byte in start_ps1[3:])
    assert b"Downloading official Python" in start_ps1
    start_bat = zf.read(f"{inner}/Start.bat")
    assert all(byte < 128 for byte in start_bat)
    assert b"\r\n" in start_bat
    assert b"\n" not in start_bat.replace(b"\r\n", b"")
    assert b"ExecutionPolicy Bypass" in start_bat
    assert b"0.3.3" in start_bat
    assert b"%TEMP%" in start_bat
    assert b"win_bootstrap.py" in start_bat
    assert b"..\\.venv\\Scripts\\python.exe" in start_bat
    fix_bat = zf.read(f"{inner}/FIX-CLASS-INTERPRETER.bat")
    assert b"fix.ps1" in fix_bat
    assert b"-TargetPath" in fix_bat
    cn_bat = zf.read(f"{inner}/启动同传.bat")
    assert cn_bat == start_bat
    assert b"\xe5\x90\xaf\xe5\x8a\xa8\xe5\xa4\xb1" not in cn_bat
    bootstrap = zf.read(f"{inner}/win_bootstrap.py")
    assert b"def stop_listener" in bootstrap
    assert b"api/shutdown" in bootstrap
    got = zf.read(f"{inner}/VERSION").decode().strip()
    assert got == version, got
    assert f"{inner}/win_bootstrap.py" in names
    assert f"{inner}/get-pip.py" in names
    assert f"{inner}/pip.pyz" in names
    assert len(zf.read(f"{inner}/pip.pyz")) > 10000
    assert f"{inner}/.runtime/python/python.exe" in names
    pth = zf.read(f"{inner}/.runtime/python/python312._pth")
    assert b"import site" in pth
    assert len(zf.read(f"{inner}/get-pip.py")) > 10000
    assert f"{inner}/secret_box.py" in names
    assert f"{inner}/deepseek_api.py" in names
    assert f"{inner}/deepseek_api.enc" in names
    enc = zf.read(f"{inner}/deepseek_api.enc")
    assert enc.startswith(b"CI1.")
    assert b"sk-" not in enc
    assert not any(name.endswith("secrets/deepseek.api") or name.endswith("/deepseek.api") for name in names)

recover_zip = root / f"ClassInterpreter-recover-{version}.zip"
assert recover_zip.is_file(), f"rebuild {recover_zip.name}"
with zipfile.ZipFile(recover_zip) as zf:
    names = zf.namelist()
    prefix = f"ClassInterpreter-recover-{version}/"
    assert "READ-ME-FIRST.txt" in names, names
    assert "INSTALL-OR-REPAIR.bat" in names, names
    assert "repair.ps1" in names, names
    recover_readme = zf.read("READ-ME-FIRST.txt")
    assert all(byte < 128 for byte in recover_readme)
    assert b"INSTALL-OR-REPAIR.bat" in recover_readme
    assert b"cutionPolicy" in recover_readme
    assert prefix + "FIX-CLASS-INTERPRETER.bat" in names
    assert prefix + "fix.ps1" in names
    start_bat = zf.read(prefix + "Start.bat")
    cn_bat = zf.read(prefix + "启动同传.bat")
    assert start_bat == cn_bat
    assert b"\r\n" in start_bat
    assert b"\n" not in start_bat.replace(b"\r\n", b"")
    assert b"def stop_listener" in zf.read(prefix + "win_bootstrap.py")
    assert not any(".runtime" in name for name in names)

print("packaging ok")
