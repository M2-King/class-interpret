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
assert latest["tag"] == f"v{version}"
assert latest["mac"] == "ClassInterpreter-mac.zip"
assert latest["windows"] == "ClassInterpreter-windows.zip"
assert latest["mac_versioned"] == f"ClassInterpreter-mac-{version}.zip"
assert latest["windows_versioned"] == f"ClassInterpreter-windows-{version}.zip"
assert latest["mac_folder"] == f"ClassInterpreter-mac-{version}"
assert latest["windows_folder"] == f"ClassInterpreter-{version}"
assert latest["banner"] == f"Class Interpreter {version}"
assert latest["github_mac"].endswith("releases/latest/download/ClassInterpreter-mac.zip")
assert latest["github_windows"].endswith("releases/latest/download/ClassInterpreter-windows.zip")
assert latest["api_latest"].endswith("repos/M2-King/class-interpret/releases/latest")
notes = (docs / "release-body.md").read_text(encoding="utf-8")
assert f"ClassInterpreter-mac-{version}.zip" in notes
assert f"ClassInterpreter-windows-{version}.zip" in notes
assert f"ClassInterpreter-{version}\\" in notes
assert f"Class Interpreter {version}" in notes
assert "OPEN-THIS.bat" in notes
assert "Open.command" in notes
assert "zipball" not in notes.lower()
readme = (root / "README.md").read_text(encoding="utf-8")
assert "releases/latest/download/ClassInterpreter-mac.zip" in readme
assert "releases/latest/download/ClassInterpreter-windows.zip" in readme
assert "python3 packaging/publish_site_packs.py" in readme
assert "api.github.com/repos/M2-King/class-interpret/releases/latest" in readme
assert "ClassInterpreter-windows-" in readme

workflow = (root / ".github/workflows/publish-install-packs.yml").read_text(encoding="utf-8")
assert "publish_site_packs.py" in workflow
assert "ClassInterpreter-mac.zip" in workflow
assert "ClassInterpreter-windows.zip" in workflow
assert "ClassInterpreter-mac-${VERSION}.zip" in workflow
assert "ClassInterpreter-windows-${VERSION}.zip" in workflow
assert "release-body.md" in workflow
assert "--notes-file" in workflow
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
    assert (fake / "docs/ClassInterpreter-windows-9.9.9.zip").is_file()
    stamped = (fake / "docs/index.html").read_text(encoding="utf-8")
    assert "9.9.9" in stamped
    assert 'href="ClassInterpreter-mac.zip"' in stamped
    meta = json.loads((fake / "docs/latest.json").read_text(encoding="utf-8"))
    assert meta["version"] == "9.9.9"
    assert meta["tag"] == "v9.9.9"
    assert meta["windows_versioned"] == "ClassInterpreter-windows-9.9.9.zip"
    assert meta["windows_folder"] == "ClassInterpreter-9.9.9"
    assert meta["banner"] == "Class Interpreter 9.9.9"
    fake_notes = (fake / "docs/release-body.md").read_text(encoding="utf-8")
    assert "ClassInterpreter-windows-9.9.9.zip" in fake_notes
    assert "ClassInterpreter-9.9.9\\" in fake_notes
    assert "Class Interpreter 9.9.9" in fake_notes
finally:
    shutil.rmtree(fake, ignore_errors=True)

print("publish site packs ok")
