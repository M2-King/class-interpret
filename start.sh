#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

ADDRESS="http://127.0.0.1:8765/"

open_local() {
  if [[ "$(uname -s)" == "Darwin" ]]; then
    open "$ADDRESS"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$ADDRESS" >/dev/null 2>&1 || true
  fi
}

service_up() {
  curl -fsS --max-time 1 "${ADDRESS}api/status" >/dev/null 2>&1
}

if service_up; then
  open_local
  exit 0
fi

# shellcheck source=bootstrap.sh
source ./bootstrap.sh
ensure_runtime

if [[ -z "${DISPLAY:-}" && "$(uname -s)" != "Darwin" ]]; then
  export CLASS_INTERPRET_NO_BROWSER=1
fi

exec "${CLASS_INTERPRET_VENV:-.venv}/bin/python" server.py
