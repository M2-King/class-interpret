#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "docs"
html = (root / "index.html").read_text(encoding="utf-8")
css = (root / "style.css").read_text(encoding="utf-8")
mac_zip = root / "ClassInterpreter-mac-0.3.3.zip"
win_zip = root / "ClassInterpreter-windows-0.3.3.zip"
assert mac_zip.is_file() and mac_zip.stat().st_size > 10_000
assert win_zip.is_file() and win_zip.stat().st_size > 10_000_000
assert "听懂每一句" in html
assert "Class Interpreter" in html
assert "Open.command" in html
assert "Start.bat" in html
assert 'href="ClassInterpreter-mac-0.3.3.zip"' in html
assert 'href="ClassInterpreter-windows-0.3.3.zip"' in html
assert html.count('href="ClassInterpreter-mac-0.3.3.zip"') >= 2
assert html.count('href="ClassInterpreter-windows-0.3.3.zip"') >= 2
assert "raw/cursor/" not in html
assert "OPEN-THIS.bat" in html
assert "Extract All" in html
assert "听课搭子手机" in html or "trycloudflare" in html
assert "iPhone" in html or "iPad" in html
assert ".venv" in html
assert "assets/app-preview.png" in html
assert "sk-" not in html
assert "sk-" not in css
assert (root / "assets/golden-landing.png").is_file()
assert (root / "assets/app-preview.png").is_file()
print("site ok")
