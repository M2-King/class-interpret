#!/usr/bin/env python3
"""Stable site pack names stay the same across versions."""
from pathlib import Path
import json
import sys
import tempfile
import shutil

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packaging"))
import publish_site_packs as pub

version = (root / "VERSION").read_text(encoding="utf-8").strip()
assert version

docs = root / "docs"
html = (docs / "index.html").read_text(encoding="utf-8")
assert 'href="ClassInterpreter-mac.zip"' in html
assert 'href="ClassInterpreter-windows.zip"' in html
assert html.count('href="ClassInterpreter-mac.zip"') >= 2
assert html.count('href="ClassInterpreter-windows.zip"') >= 2
assert 'href="ClassInterpreter-mac-' not in html
assert 'href="ClassInterpreter-windows-' not in html
assert (docs / "ClassInterpreter-mac.zip").is_file()
assert (docs / "ClassInterpreter-windows.zip").is_file()
assert (docs / "ClassInterpreter-windows.zip").stat().st_size > 10_000_000
latest = json.loads((docs / "latest.json").read_text(encoding="utf-8"))
assert latest["version"] == version
assert latest["mac"] == "ClassInterpreter-mac.zip"
assert latest["windows"] == "ClassInterpreter-windows.zip"
assert latest["github_mac"].endswith("releases/latest/download/ClassInterpreter-mac.zip")
assert latest["github_windows"].endswith("releases/latest/download/ClassInterpreter-windows.zip")
readme = (root / "README.md").read_text(encoding="utf-8")
assert "releases/latest/download/ClassInterpreter-mac.zip" in readme
assert "releases/latest/download/ClassInterpreter-windows.zip" in readme
assert "python3 packaging/publish_site_packs.py" in readme

workflow = (root / ".github/workflows/publish-install-packs.yml").read_text(encoding="utf-8")
assert "publish_site_packs.py" in workflow
assert "ClassInterpreter-mac.zip" in workflow
assert "ClassInterpreter-windows.zip" in workflow
assert "gh release" in workflow
assert "tags:" in workflow

fake = Path(tempfile.mkdtemp(prefix="ci-publish-"))
try:
    (fake / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    (fake / "docs").mkdir()
    (fake / "docs" / "index.html").write_text(
        '<a href="ClassInterpreter-mac.zip">Mac 0.0.0</a>'
        '<a href="ClassInterpreter-windows.zip">Windows 0.0.0</a>'
        '<span>0.0.0</span>',
        encoding="utf-8",
    )
    (fake / "ClassInterpreter-mac-9.9.9.zip").write_bytes(b"mac-pack" * 2000)
    (fake / "ClassInterpreter-windows-9.9.9.zip").write_bytes(b"win-pack" * 2000)
    pub.publish(fake)
    assert (fake / "docs/ClassInterpreter-mac.zip").read_bytes().startswith(b"mac-pack")
    assert (fake / "docs/ClassInterpreter-windows.zip").read_bytes().startswith(b"win-pack")
    assert (fake / "docs/ClassInterpreter-mac-9.9.9.zip").is_file()
    stamped = (fake / "docs/index.html").read_text(encoding="utf-8")
    assert "9.9.9" in stamped
    assert 'href="ClassInterpreter-mac.zip"' in stamped
    meta = json.loads((fake / "docs/latest.json").read_text(encoding="utf-8"))
    assert meta["version"] == "9.9.9"
finally:
    shutil.rmtree(fake, ignore_errors=True)

print("publish site packs ok")
