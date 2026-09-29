#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
STAGE="$(mktemp -d)"
DEST_NAME="ClassInterpreter-${VERSION}"
DEST="$STAGE/$DEST_NAME"
export DEST
mkdir -p "$DEST"
for f in Start.bat 启动同传.bat start.ps1 server.py setup_models.py setup_whisper.py setup_deepseek.py ssl_certs.py whisper_hub.py deepseek_hub.py \
         requirements.txt index.html app.js style.css VERSION README.md; do
  cp "$ROOT/$f" "$DEST/"
done
cp "$ROOT/packaging/windows/HOW-TO-START.txt" "$DEST/"
cp "$ROOT/packaging/windows/使用说明.txt" "$DEST/"
cp "$ROOT/packaging/windows/READ-ME-FIRST.txt" "$STAGE/READ-ME-FIRST.txt"
python3 - <<'PY'
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
PY
OUT_VER="$ROOT/ClassInterpreter-windows-${VERSION}.zip"
OUT_STABLE="$ROOT/ClassInterpreter-windows.zip"
rm -f "$OUT_VER" "$OUT_STABLE"
(
  cd "$STAGE"
  zip -r "$OUT_VER" READ-ME-FIRST.txt "$DEST_NAME"
)
cp "$OUT_VER" "$OUT_STABLE"
rm -rf "$STAGE"
echo "Wrote $OUT_VER"
echo "Wrote $OUT_STABLE"
