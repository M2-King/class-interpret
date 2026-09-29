#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STAGE="$(mktemp -d)"
DEST="$STAGE/听课搭子"
mkdir -p "$DEST"
for f in 启动同传.bat start.ps1 server.py setup_models.py setup_whisper.py ssl_certs.py whisper_hub.py \
         requirements.txt index.html app.js style.css VERSION README.md; do
  cp "$ROOT/$f" "$DEST/"
done
rm -f "$ROOT/ClassInterpreter-windows.zip"
(
  cd "$STAGE"
  zip -r "$ROOT/ClassInterpreter-windows.zip" 听课搭子
)
rm -rf "$STAGE"
echo "Wrote $ROOT/ClassInterpreter-windows.zip"
