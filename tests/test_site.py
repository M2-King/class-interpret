#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "docs"
html = (root / "index.html").read_text(encoding="utf-8")
css = (root / "style.css").read_text(encoding="utf-8")
assert "听懂每一句" in html
assert "Class Interpreter" in html
assert "Open.command" in html
assert "Start.bat" in html
assert "ClassInterpreter-mac-0.3.3.zip" in html
assert "ClassInterpreter-windows-0.3.3.zip" in html
assert "windows-extract-guard-b27d" in html
assert "OPEN-THIS.bat" in html
assert "assets/app-preview.png" in html
assert "sk-" not in html
assert "sk-" not in css
assert (root / "assets/golden-landing.png").is_file()
assert (root / "assets/app-preview.png").is_file()
print("site ok")
