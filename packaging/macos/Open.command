#!/bin/bash
# Run this if 听课搭子.app says it cannot be opened.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/听课搭子.app"
chmod +x "$APP/Contents/MacOS/launcher" "$APP/Contents/Resources/app/bootstrap.sh" 2>/dev/null || true
xattr -cr "$APP" "$DIR" 2>/dev/null || true
# Launch Services often blocks unsigned .app downloads; run the script directly.
exec "$APP/Contents/MacOS/launcher"
