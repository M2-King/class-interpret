#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STAGE="$(mktemp -d)"
DEST="$STAGE/ClassInterpreter"
export DEST
mkdir -p "$DEST"
for f in 启动同传.bat start.ps1 server.py setup_models.py setup_whisper.py ssl_certs.py whisper_hub.py \
         requirements.txt index.html app.js style.css VERSION README.md; do
  cp "$ROOT/$f" "$DEST/"
done
python3 - <<'PY'
from pathlib import Path
import os
dest = Path(os.environ["DEST"])
p = dest / "start.ps1"
text = p.read_text(encoding="utf-8-sig")
p.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
PY
rm -f "$ROOT/ClassInterpreter-windows.zip"
(
  cd "$STAGE"
  zip -r "$ROOT/ClassInterpreter-windows.zip" ClassInterpreter
)
rm -rf "$STAGE"
echo "Wrote $ROOT/ClassInterpreter-windows.zip"
