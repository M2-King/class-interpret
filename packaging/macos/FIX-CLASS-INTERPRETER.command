#!/bin/bash
# Download a clean package and repair the app beside this command.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$DIR/听课搭子.app"
URL="https://raw.githubusercontent.com/M2-King/class-interpret/codex/ui2-cross-platform/ClassInterpreter-mac-0.3.3.zip"
TMP="$(mktemp -d /tmp/ClassInterpreter-fix.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

printf '%s\n' 'Downloading Class Interpreter 0.3.3...'
curl -fL --retry 3 --connect-timeout 20 -o "$TMP/package.zip" "$URL"
[[ "$(stat -f '%z' "$TMP/package.zip")" -gt 10000 ]] || { echo 'Downloaded package is incomplete.' >&2; exit 1; }
/usr/bin/ditto -x -k "$TMP/package.zip" "$TMP/package"
REPAIR="$(find "$TMP/package" -maxdepth 3 -type f -name 'INSTALL-OR-REPAIR.command' -print -quit)"
[[ -n "$REPAIR" ]] || { echo 'Repair tool is missing from the package.' >&2; exit 1; }
chmod +x "$REPAIR"
exec "$REPAIR" "$TARGET"
