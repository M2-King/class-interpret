#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$ROOT/听课搭子.app"
DEST="$APP/Contents/Resources/app"
mkdir -p "$DEST"
for f in server.py streaming_server.py streaming_hub.py translation_hub.py setup_models.py setup_whisper.py setup_deepseek.py ssl_certs.py whisper_hub.py deepseek_hub.py \
         deepseek_api.py secret_box.py requirements.txt bootstrap.sh \
         index.html app.js audio-worklet.js subtitle-window.js subtitle.html style.css subtitle.css VERSION; do
  cp "$ROOT/$f" "$DEST/"
done
if [[ -f "$ROOT/deepseek_api.enc" ]]; then
  cp "$ROOT/deepseek_api.enc" "$DEST/"
fi
chmod +x "$APP/Contents/MacOS/launcher" "$DEST/bootstrap.sh"
printf 'APPL????' > "$APP/Contents/PkgInfo"
echo "Assembled $DEST"
