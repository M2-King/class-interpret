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
    "0.3.3",
    ".runtime\\python",
    "python-3.12.10",
    "mirrors.huaweicloud.com/python",
    "InstallAllUsers=0",
    "TargetDir",
    "WindowsApps",
    "embed-arm64",
    "python-3.12.10-embed-",
    "python-3.12.10-arm64.exe",
    "Downloading official Python",
    "ConvertTo-PythonPath",
    "Invoke-Native",
    "-sS",
    "LastNativeExit",
    "ForEach-Object { Write-Host $_ }",
    "._pth",
    "Ensure-LocalPip",
    "get-pip.py",
    "pip.pyz",
    "anaconda3",
    "-3",
    "AppData\\Local\\Temp",
    "Extract All",
    "env:TEMP",
    "tuna.tsinghua",
    "embed-arm64",
    "python-3.12.10-arm64.exe",
    "nvidia-cublas-cu12",
    "CUDA libs skipped",
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

def assert_crlf_bat(raw: bytes, name: str) -> None:
    leftover = raw.replace(b"\r\n", b"")
    assert b"\n" not in leftover, (
        f"{name} must use CRLF. Unix LF on Chinese Windows cmd.exe splits "
        "-ExecutionPolicy so it tries to run cutionPolicy"
    )
    assert b"\r\n" in raw, name


start_bat = (root / "Start.bat").read_bytes()
assert (root / "Start.bat").is_file(), "ASCII Start.bat is the Windows double-click entry"
assert all(byte < 128 for byte in start_bat), "Start.bat must be ASCII"
assert_crlf_bat(start_bat, "Start.bat")
assert b"start.ps1" in start_bat
assert b"Extract All" in start_bat
assert b"AppData\\Local\\Temp" in start_bat or b"Local\\Temp" in start_bat
assert b"%TEMP%" in start_bat
assert b"server.py" in start_bat
assert b"-File" in start_bat
assert b"Unblock-File" in start_bat
assert b"0.3.3" in start_bat
assert b"win_bootstrap.py" in start_bat
assert b".runtime\\python\\python.exe" in start_bat
assert b".venv\\Scripts\\python.exe" in start_bat
assert b"..\\.venv\\Scripts\\python.exe" in start_bat
assert start_bat.find(b".venv\\Scripts\\python.exe") < start_bat.find(b"ExecutionPolicy")
assert start_bat.find(b"..\\.venv\\Scripts\\python.exe") < start_bat.find(b".runtime\\python\\python.exe")
assert b"if exist \"%~dp0start.ps1\" goto :NEEDPS" in start_bat
assert start_bat.find(b"if exist \"%~dp0start.ps1\" goto :NEEDPS") < start_bat.find(
    b"if exist \"%~dp0.runtime\\python\\python.exe\" goto :BUNDLE"
), "deleted .venv must recreate via start.ps1 before bundled Python/get-pip"

cn_bat = (root / "启动同传.bat").read_bytes()
assert all(byte < 128 for byte in cn_bat), "启动同传.bat must be ASCII"
assert_crlf_bat(cn_bat, "启动同传.bat")
assert b"\xe5\x90\xaf\xe5\x8a\xa8\xe5\xa4\xb1" not in cn_bat, "old UTF-8 启动失败 bat breaks cmd.exe"
assert b"\xe6\x8c\x89\xe4\xbb\xbb\xe6\x84\x8f\xe9\x94\xae" not in cn_bat, "old 按任意键 line"
assert len(cn_bat) != 202, "202-byte original 启动同传.bat is the cutionPolicy launcher"
assert cn_bat == start_bat, "启动同传.bat must be a full launcher; R9000P copies often lack Start.bat"

attrs = (root / ".gitattributes").read_text(encoding="utf-8")
assert "*.bat" in attrs and "-text" in attrs, "keep CRLF bytes in git so cmd.exe can parse the bats"

open_this = (root / "packaging/windows/OPEN-THIS.bat").read_bytes()
assert all(byte < 128 for byte in open_this), "OPEN-THIS.bat must be ASCII"
assert_crlf_bat(open_this, "OPEN-THIS.bat")
assert b"Extract All" in open_this
assert b"ClassInterpreter-0.3.3" in open_this
assert b"Start.bat" in open_this
assert b"%TEMP%" in open_this

howto = (root / "packaging/windows/HOW-TO-START.txt").read_bytes()
assert all(byte < 128 for byte in howto)
assert b"Start.bat" in howto
assert b"OPEN-THIS.bat" in howto
assert b"0.3.3" in howto
assert b"ClassInterpreter-windows-0.3.3.zip" in howto or b"0.3.3" in howto

print("start.ps1 ok")
