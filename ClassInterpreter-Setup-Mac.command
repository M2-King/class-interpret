#!/bin/bash
# Standalone macOS installer: download, extract, install/repair, and launch.
set -euo pipefail

VERSION="0.3.3"
URL="https://github.com/M2-King/class-interpret/releases/download/v${VERSION}/ClassInterpreter-mac-${VERSION}.zip"
MODEL_URL="https://github.com/M2-King/class-interpret/releases/download/v${VERSION}/ClassInterpreter-Model-Small.zip"
TMP="$(mktemp -d /tmp/ClassInterpreter-setup.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

printf '%s\n' "Downloading Class Interpreter ${VERSION}..."
curl -fL --retry 3 --connect-timeout 20 -o "$TMP/package.zip" "$URL"
[[ "$(stat -f '%z' "$TMP/package.zip")" -gt 10000 ]] || { echo 'Downloaded package is incomplete.' >&2; exit 1; }
/usr/bin/ditto -x -k "$TMP/package.zip" "$TMP/package"
REPAIR="$(find "$TMP/package" -maxdepth 3 -type f -name 'INSTALL-OR-REPAIR.command' -print -quit)"
[[ -n "$REPAIR" ]] || { echo 'Repair tool is missing from the package.' >&2; exit 1; }

SUPPORT="$HOME/Library/Application Support/ClassInterpret"
MODEL="$SUPPORT/hf/bundled/faster-whisper-small/model.bin"
if [[ ! -f "$MODEL" || "$(stat -f '%z' "$MODEL")" -lt 400000000 ]]; then
  printf '%s\n' 'Downloading the ready-to-use Small offline speech model (about 465 MB)...'
  curl -fL --retry 3 --connect-timeout 20 -o "$TMP/model.zip" "$MODEL_URL"
  [[ "$(stat -f '%z' "$TMP/model.zip")" -gt 400000000 ]] || { echo 'Downloaded speech model is incomplete.' >&2; exit 1; }
  mkdir -p "$SUPPORT/hf/bundled"
  /usr/bin/ditto -x -k "$TMP/model.zip" "$SUPPORT/hf/bundled"
  [[ -f "$MODEL" && "$(stat -f '%z' "$MODEL")" -gt 400000000 ]] || { echo 'Speech model could not be installed.' >&2; exit 1; }
else
  printf '%s\n' 'Existing Small offline speech model preserved.'
fi

chmod +x "$REPAIR"
"$REPAIR"
