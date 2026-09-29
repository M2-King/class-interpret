#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
script = (root / "start.ps1").read_text(encoding="utf-8")
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
