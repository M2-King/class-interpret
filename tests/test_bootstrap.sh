#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=bootstrap.sh
source ./bootstrap.sh

os="$(uname -s)"
[[ -n "$os" ]]

found="$(find_python)"
[[ -n "$found" ]]
python_ok "$found"
"$found" -c 'import venv, sys; assert (3, 10) <= sys.version_info[:2] <= (3, 12)'

PYTHON="$found"
ensure_python
[[ "$PYTHON" == "$found" ]]

type service_up >/dev/null
type stop_existing_server >/dev/null
type pip_with_ssl_fallback >/dev/null
[[ "$(app_version VERSION)" == "0.2.2" ]]

"$found" tests/test_ssl.py

echo "bootstrap ok: os=$os python=$PYTHON"
