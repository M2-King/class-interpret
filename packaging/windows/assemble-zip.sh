#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
STAGE="$(mktemp -d)"
DEST_NAME="ClassInterpreter-${VERSION}"
DEST="$STAGE/$DEST_NAME"
export DEST
mkdir -p "$DEST"
for f in Start.bat 启动同传.bat FIX-CLASS-INTERPRETER.bat start.ps1 fix.ps1 win_bootstrap.py server.py streaming_server.py streaming_hub.py translation_hub.py setup_models.py setup_whisper.py setup_deepseek.py ssl_certs.py whisper_hub.py deepseek_hub.py \
         deepseek_api.py secret_box.py requirements.txt index.html app.js audio-worklet.js subtitle-window.js subtitle.html style.css subtitle.css VERSION README.md; do
  cp "$ROOT/$f" "$DEST/"
done
if [[ -f "$ROOT/deepseek_api.enc" ]]; then
  cp "$ROOT/deepseek_api.enc" "$DEST/"
fi
if [[ -f "$ROOT/pip.pyz" ]]; then
  cp "$ROOT/pip.pyz" "$DEST/"
elif [[ -f "$ROOT/packaging/windows/cache/pip.pyz" ]]; then
  cp "$ROOT/packaging/windows/cache/pip.pyz" "$DEST/pip.pyz"
fi
cp "$ROOT/packaging/windows/HOW-TO-START.txt" "$DEST/"
cp "$ROOT/packaging/windows/使用说明.txt" "$DEST/"
cp "$ROOT/packaging/windows/READ-ME-FIRST.txt" "$STAGE/READ-ME-FIRST.txt"
cp "$ROOT/packaging/windows/OPEN-THIS.bat" "$STAGE/OPEN-THIS.bat"
cp "$ROOT/packaging/windows/INSTALL-OR-REPAIR.bat" "$STAGE/INSTALL-OR-REPAIR.bat"
cp "$ROOT/packaging/windows/repair.ps1" "$STAGE/repair.ps1"
export DEST
PYTHON="${PYTHON:-python3}"
"$PYTHON" "$ROOT/packaging/windows/bundle_runtime.py"
"$PYTHON" - <<'PY'
from pathlib import Path
import os
dest = Path(os.environ["DEST"])
p = dest / "start.ps1"
text = p.read_text(encoding="utf-8-sig")
if any(ord(ch) > 127 for ch in text):
    raise SystemExit("start.ps1 must stay ASCII so Windows PowerShell 5.1 can parse it")
p.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
howto = dest / "使用说明.txt"
howto.write_bytes(b"\xef\xbb\xbf" + howto.read_text(encoding="utf-8-sig").encode("utf-8"))
for bat_name in ("Start.bat", "启动同传.bat"):
    bat = dest / bat_name
    body = bat.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    if not all(byte < 128 for byte in body):
        raise SystemExit(bat_name + " must stay ASCII")
    bat.write_bytes(body)
open_this = Path(os.environ["DEST"]).parent / "OPEN-THIS.bat"
open_body = open_this.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
open_this.write_bytes(open_body)
installer = Path(os.environ["DEST"]).parent / "INSTALL-OR-REPAIR.bat"
installer_body = installer.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
installer.write_bytes(installer_body)
PY
OUT_VER="$ROOT/ClassInterpreter-windows-${VERSION}.zip"
OUT_STABLE="$ROOT/ClassInterpreter-windows.zip"
rm -f "$OUT_VER" "$OUT_STABLE"
export STAGE DEST_NAME OUT_VER
"$PYTHON" - <<'PY'
from pathlib import Path
import os
import zipfile

stage = Path(os.environ["STAGE"])
out = Path(os.environ["OUT_VER"])
dest_name = os.environ["DEST_NAME"]
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for name in ("READ-ME-FIRST.txt", "OPEN-THIS.bat", "INSTALL-OR-REPAIR.bat", "repair.ps1"):
        zf.write(stage / name, name)
    for path in (stage / dest_name).rglob("*"):
        if path.is_file():
            zf.write(path, path.relative_to(stage).as_posix())
PY
cp "$OUT_VER" "$OUT_STABLE"
export ROOT VERSION
"$PYTHON" - <<'PY'
from pathlib import Path
import os
import zipfile

root = Path(os.environ["ROOT"])
version = os.environ["VERSION"]
out = root / f"ClassInterpreter-recover-{version}.zip"
inner = f"ClassInterpreter-recover-{version}"
names = [
    "Start.bat",
    "启动同传.bat",
    "FIX-CLASS-INTERPRETER.bat",
    "start.ps1",
    "fix.ps1",
    "win_bootstrap.py",
    "server.py",
    "streaming_server.py",
    "streaming_hub.py",
    "translation_hub.py",
    "setup_models.py",
    "setup_whisper.py",
    "setup_deepseek.py",
    "ssl_certs.py",
    "whisper_hub.py",
    "deepseek_hub.py",
    "deepseek_api.py",
    "secret_box.py",
    "requirements.txt",
    "index.html",
    "app.js",
    "audio-worklet.js",
    "subtitle-window.js",
    "subtitle.html",
    "style.css",
    "subtitle.css",
    "VERSION",
    "README.md",
    "pip.pyz",
]
readme = (
    "STOP. Recover pack after a broken launch or a deleted .venv.\r\n"
    "\r\n"
    "1. Right-click this zip -> Extract All.\r\n"
    "2. Double-click INSTALL-OR-REPAIR.bat. It finds the old app folder.\r\n"
    "3. It preserves data/models, backs up app files, and rebuilds broken .venv.\r\n"
    "4. Phone hotspot only if package download fails.\r\n"
    "5. Keep the black window open while first-run packages install.\r\n"
    "   First line must be Class Interpreter 0.3.3\r\n"
    "   Status must say 0.3.3, not v0.2.2.\r\n"
    "\r\n"
    "Do not click OPEN-THIS.bat from inside the zip window.\r\n"
    "If the black window says cutionPolicy, you clicked the old starter.\r\n"
).encode("ascii")
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("READ-ME-FIRST.txt", readme)
    for outer in ("INSTALL-OR-REPAIR.bat", "repair.ps1"):
        data = (root / "packaging/windows" / outer).read_bytes()
        if outer.endswith(".bat"):
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        zf.writestr(outer, data)
    for name in names:
        path = root / name
        if not path.is_file():
            continue
        data = path.read_bytes()
        if name.endswith(".bat"):
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        zf.writestr(f"{inner}/{name}", data)
    howto = (root / "packaging/windows/HOW-TO-START.txt").read_bytes()
    zf.writestr(f"{inner}/HOW-TO-START.txt", howto.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    zh = (root / "packaging/windows/使用说明.txt").read_bytes()
    if not zh.startswith(b"\xef\xbb\xbf"):
        zh = b"\xef\xbb\xbf" + zh
    zf.writestr(f"{inner}/使用说明.txt", zh)
    enc = root / "deepseek_api.enc"
    if enc.is_file():
        zf.writestr(f"{inner}/deepseek_api.enc", enc.read_bytes())
print("Wrote", out)
PY
rm -rf "$STAGE"
echo "Wrote $OUT_VER"
echo "Wrote $OUT_STABLE"
