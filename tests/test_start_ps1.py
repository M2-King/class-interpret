#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
raw = (root / "start.ps1").read_bytes()
assert raw.startswith(b"\xef\xbb\xbf"), "start.ps1 needs UTF-8 BOM for Windows PowerShell 5.1"
assert b"\xe2\x80\x93" not in raw, "en-dash breaks Windows PowerShell without BOM"
body = raw[3:]
assert all(byte < 128 for byte in body), (
    "start.ps1 must be ASCII after the BOM; PowerShell 5.1 misparses UTF-8 Chinese"
)
script = raw.decode("utf-8-sig")
for token in (
    "HF_ENDPOINT",
    "hf-mirror.com",
    "trusted-host",
    "certifi",
    "api/shutdown",
    "status.version",
    "0.2.9",
    ".runtime\\python",
    "python-3.12.10",
    "mirrors.huaweicloud.com/python",
    "InstallAllUsers=0",
    "TargetDir",
    "WindowsApps",
    "embed-amd64",
    "get-pip.py",
    "Downloading official Python",
    "ConvertTo-PythonPath",
    "Invoke-Native",
    "-sS",
    "LastNativeExit",
    "ForEach-Object { Write-Host $_ }",
    "._pth",
    "Ensure-LocalPip",
    "anaconda3",
    "-3",
):
    assert token in script, token
assert "curl.exe @curlArgs 2>$null" not in script
assert "Filter '*.pth'" not in script

import fnmatch
assert not fnmatch.fnmatch("python312._pth", "*.pth")
assert fnmatch.fnmatch("python312._pth", "python*._pth")

import re

regex_line = [ln for ln in script.splitlines() if "$regex =" in ln]
assert regex_line, "ConvertTo-PythonPath must define $regex"
ps_pat = regex_line[0].split("=", 1)[1].strip().strip("'")
blob = "\n".join(
    [
        "Collecting pip",
        "Using cached pip-26.2.1-py3-none-any.whl",
        "Successfully installed pip-26.2.1",
        r"C:\Users\26098681\Downloads\ClassInterpreter-windows-0.2.6\ClassInterpreter-0.2.6\.runtime\python\python.exe",
    ]
)
match = re.search(ps_pat, blob)
assert match, (ps_pat, blob)
assert match.group(1).endswith("python.exe")
assert "Collecting" not in match.group(1)
joined = "Collecting pip Using cached pip " + r"C:\Users\26098681\a\.runtime\python\python.exe"
match = re.search(ps_pat, joined)
assert match.group(1).endswith(r".runtime\python\python.exe")

start_bat = (root / "Start.bat").read_bytes()
assert (root / "Start.bat").is_file(), "ASCII Start.bat is the Windows double-click entry"
assert all(byte < 128 for byte in start_bat), "Start.bat must be ASCII"
assert b"start.ps1" in start_bat
assert b"ExecutionPolicy Bypass" in start_bat
assert b"-File" in start_bat
assert b"Unblock-File" in start_bat

cn_bat = (root / "启动同传.bat").read_bytes()
assert all(byte < 128 for byte in cn_bat), "启动同传.bat must be ASCII"
assert b"start.ps1" in cn_bat or b"Start.bat" in cn_bat
assert b"ExecutionPolicy Bypass" in cn_bat or b"Start.bat" in cn_bat

howto = (root / "packaging/windows/HOW-TO-START.txt").read_bytes()
assert all(byte < 128 for byte in howto)
assert b"Start.bat" in howto
assert b"0.2.9" in howto
assert b"ClassInterpreter-windows-0.2.9.zip" in howto or b"0.2.9" in howto

print("start.ps1 ok")
