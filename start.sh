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

if python3 -c "import urllib.request; urllib.request.urlopen('${ADDRESS}api/status', timeout=1)" >/dev/null 2>&1; then
  open_local
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 Python 3。请安装 Python 3.10–3.12 后再运行。" >&2
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
if ! .venv/bin/python setup_models.py; then
  echo "翻译模型暂未安装；识别仍可使用，安装模型后会显示中文译文。" >&2
fi

# Headless Linux (SSH/tmux) has no GUI; macOS and desktop Linux should open a browser.
if [[ -z "${DISPLAY:-}" && "$(uname -s)" != "Darwin" ]]; then
  export CLASS_INTERPRET_NO_BROWSER=1
fi

exec .venv/bin/python server.py
