#!/bin/bash
# Install or repair Class Interpreter without deleting recordings, models, or settings.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$DIR/听课搭子.app"
REQUESTED_TARGET="${1:-}"
SUPPORT="$HOME/Library/Application Support/ClassInterpret"
LOG="$HOME/Library/Logs/class-interpret-repair.log"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$HOME/Library/Logs" "$SUPPORT/repair-backups"
: > "$LOG"
log() {
  printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG"
}
fail() {
  log "FAILED: $*"
  osascript -e "display dialog \"Repair failed. Details: ~/Library/Logs/class-interpret-repair.log\" with title \"Class Interpreter\" buttons {\"OK\"} default button 1" >/dev/null 2>&1 || true
  exit 1
}

[[ -d "$SOURCE/Contents/Resources/app" ]] || fail "The clean app is missing. Extract the complete Mac zip first."
log "Clean package: $SOURCE"

TARGET="$REQUESTED_TARGET"
best_time=0
consider() {
  local candidate=$1 modified=0
  [[ -d "$candidate/Contents/Resources/app" ]] || return 0
  [[ "$candidate" == "$SOURCE" ]] && return 0
  modified="$(stat -f '%m' "$candidate" 2>/dev/null || printf '0')"
  if [[ "$modified" -gt "$best_time" ]]; then
    TARGET="$candidate"
    best_time="$modified"
  fi
}

if [[ -z "$TARGET" ]]; then
  consider "/Applications/听课搭子.app"
  consider "$HOME/Applications/听课搭子.app"
  for root in "$HOME/Desktop" "$HOME/Downloads" "$HOME/Documents"; do
    [[ -d "$root" ]] || continue
    while IFS= read -r -d '' candidate; do
      consider "$candidate"
    done < <(find "$root" -maxdepth 4 -type d -name '听课搭子.app' -print0 2>/dev/null)
  done
fi

if [[ -z "$TARGET" ]]; then
  mkdir -p "$HOME/Applications"
  TARGET="$HOME/Applications/听课搭子.app"
fi
TARGET="$(cd "$(dirname "$TARGET")" 2>/dev/null && pwd)/$(basename "$TARGET")"
log "Detected installation: $TARGET"

if [[ -d "$TARGET" && "$TARGET" != "$SOURCE" ]]; then
  BACKUP="$SUPPORT/repair-backups/听课搭子-$STAMP.app"
  ditto "$TARGET" "$BACKUP" || fail "Could not back up the existing app."
  log "Backup: $BACKUP"
fi

if [[ "$TARGET" != "$SOURCE" ]]; then
  parent="$(dirname "$TARGET")"
  if [[ -w "$parent" ]]; then
    rm -rf "$TARGET"
    ditto "$SOURCE" "$TARGET" || fail "Could not copy the repaired app."
  else
    /usr/bin/osascript - "$SOURCE" "$TARGET" <<'APPLESCRIPT' || fail "Administrator copy was cancelled."
on run argv
  set sourcePath to item 1 of argv
  set targetPath to item 2 of argv
  do shell script "/bin/rm -rf " & quoted form of targetPath & "; /usr/bin/ditto " & quoted form of sourcePath & " " & quoted form of targetPath with administrator privileges
end run
APPLESCRIPT
  fi
  log "Restored official application files."
fi

VENV="$SUPPORT/venv"
if [[ -d "$VENV" ]]; then
  if [[ ! -x "$VENV/bin/python" ]] || ! "$VENV/bin/python" -c 'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)' >/dev/null 2>&1; then
    QUARANTINE="$SUPPORT/venv-broken-$STAMP"
    mv "$VENV" "$QUARANTINE" || fail "Could not quarantine the broken Python environment."
    log "Quarantined broken environment: $QUARANTINE"
  fi
fi

chmod +x "$TARGET/Contents/MacOS/launcher" "$TARGET/Contents/Resources/app/bootstrap.sh" 2>/dev/null || true
xattr -cr "$TARGET" 2>/dev/null || true
log "Repair completed. Recordings, models, and settings were preserved."
log "Starting Class Interpreter..."
"$TARGET/Contents/MacOS/launcher" &
disown || true

osascript -e "display notification \"Repair complete. Class Interpreter is starting.\" with title \"Class Interpreter\"" >/dev/null 2>&1 || true
exit 0
