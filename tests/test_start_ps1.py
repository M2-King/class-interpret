#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
raw = (root / "start.ps1").read_bytes()
assert raw.startswith(b"\xef\xbb\xbf"), "start.ps1 needs UTF-8 BOM for Windows PowerShell 5.1"
assert b"\xe2\x80\x93" not in raw, "en-dash breaks Windows PowerShell without BOM"
script = raw.decode("utf-8-sig")
for token in (
    "HF_ENDPOINT",
    "hf-mirror.com",
    "trusted-host",
    "certifi",
    "api/shutdown",
    "status.version",
    "Add python.exe to PATH",
):
    assert token in script, token
print("start.ps1 ok")
