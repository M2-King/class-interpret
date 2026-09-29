#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

ADDRESS="http://127.0.0.1:8765/"

open_local() {
  local version
  version="$(app_version VERSION)"
  if [[ "$(uname -s)" == "Darwin" ]]; then
    open "${ADDRESS}?v=${version}"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${ADDRESS}?v=${version}" >/dev/null 2>&1 || true
  fi
}

# shellcheck source=bootstrap.sh
source ./bootstrap.sh

if service_up && version_matches "$(app_version VERSION)"; then
  open_local
  exit 0
fi

if service_up; then
  echo "发现旧版听课搭子，正在替换为新版……"
  stop_existing_server
fi

if [[ "$(uname -s)" == Darwin ]]; then
  export CLASS_INTERPRET_CERTS="${CLASS_INTERPRET_CERTS:-$HOME/Library/Application Support/ClassInterpret/certs.pem}"
  export CLASS_INTERPRET_MODELS="${CLASS_INTERPRET_MODELS:-$HOME/Library/Application Support/ClassInterpret/models}"
  export CLASS_INTERPRET_HF="${CLASS_INTERPRET_HF:-$HOME/Library/Application Support/ClassInterpret/hf}"
  export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
  mkdir -p "$(dirname "$CLASS_INTERPRET_CERTS")" "$HOME/Library/Application Support/ClassInterpret/data" "$CLASS_INTERPRET_HF"
fi

ensure_runtime

if [[ -z "${DISPLAY:-}" && "$(uname -s)" != "Darwin" ]]; then
  export CLASS_INTERPRET_NO_BROWSER=1
fi

exec "${CLASS_INTERPRET_VENV:-.venv}/bin/python" server.py
