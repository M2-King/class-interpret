#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$ROOT/听课搭子.app"
DEST="$APP/Contents/Resources/app"
mkdir -p "$DEST"
for f in server.py setup_models.py setup_whisper.py ssl_certs.py whisper_hub.py requirements.txt bootstrap.sh \
         index.html app.js style.css VERSION; do
  cp "$ROOT/$f" "$DEST/"
done
chmod +x "$APP/Contents/MacOS/launcher"
echo "Assembled $DEST"
