#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "docs"
html = (root / "index.html").read_text(encoding="utf-8")
css = (root / "style.css").read_text(encoding="utf-8")
mac_zip = root / "ClassInterpreter-mac.zip"
win_zip = root / "ClassInterpreter-windows.zip"
assert mac_zip.is_file() and mac_zip.stat().st_size > 10_000
assert win_zip.is_file() and win_zip.stat().st_size > 10_000_000
assert "听懂每一句" in html
assert "Class Interpreter" in html
assert "Open.command" in html
assert "Start.bat" in html
assert 'href="ClassInterpreter-mac.zip"' in html
assert 'href="ClassInterpreter-windows.zip"' in html
assert html.count('href="ClassInterpreter-mac.zip"') >= 2
assert html.count('href="ClassInterpreter-windows.zip"') >= 2
assert 'href="ClassInterpreter-mac-' not in html
assert 'href="ClassInterpreter-windows-' not in html
assert "raw/cursor/" not in html
assert "OPEN-THIS.bat" in html
assert "Extract All" in html
assert "ClassInterpreter-Setup-Windows.bat" in html
assert "ClassInterpreter-Setup-Mac.command" in html
assert "FIX-CLASS-INTERPRETER" in html
assert "听课搭子手机" in html or "trycloudflare" in html
assert "iPhone" in html or "iPad" in html
assert ".venv" in html
assert "assets/app-preview.png" in html
assert "sk-" not in html
assert "sk-" not in css
assert (root / "assets/golden-landing.png").is_file()
assert (root / "assets/app-preview.png").is_file()
print("site ok")
