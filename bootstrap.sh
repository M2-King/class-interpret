#!/usr/bin/env bash
# Shared by start.sh and start-tunnel.sh. Detects OS and installs missing runtimes.

python_ok() {
  local bin=$1
  [[ -n "$bin" && -x "$bin" ]] || return 1
  "$bin" -c 'import sys, venv
raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)' >/dev/null 2>&1
}

load_brew() {
  if command -v brew >/dev/null 2>&1; then
    return 0
  fi
  local brew_bin
  for brew_bin in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    if [[ -x "$brew_bin" ]]; then
      eval "$("$brew_bin" shellenv)"
      return 0
    fi
  done
  return 1
}

find_python() {
  local bin prefix
  load_brew || true
  if command -v brew >/dev/null 2>&1; then
    for prefix in python@3.12 python@3.11 python@3.10; do
      bin="$(brew --prefix "$prefix" 2>/dev/null)/bin/python${prefix##*@}"
      if python_ok "$bin"; then
        printf '%s\n' "$bin"
        return 0
      fi
    done
  fi
  for bin in python3.12 python3.11 python3.10 python3 \
    /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12 \
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.10/bin/python3; do
    if command -v "$bin" >/dev/null 2>&1; then
      bin="$(command -v "$bin")"
    fi
    if python_ok "$bin"; then
      printf '%s\n' "$bin"
      return 0
    fi
  done
  return 1
}

ensure_brew() {
  if load_brew; then
    return 0
  fi
  echo "未找到 Homebrew，正在安装（可能要求输入 Mac 登录密码，需要几分钟）……"
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if ! load_brew; then
    echo "Homebrew 安装后仍不在 PATH。请关闭窗口后重试，或把 /opt/homebrew/bin 加入 PATH。" >&2
    return 1
  fi
}

ensure_python() {
  local found
  if found="$(find_python)"; then
    PYTHON="$found"
    return 0
  fi
  case "$(uname -s)" in
    Darwin)
      echo "未找到 Python 3.10–3.12，正在通过 Homebrew 安装 python@3.12……"
      ensure_brew
      brew install python@3.12
      ;;
    Linux)
      echo "未找到 Python 3.10–3.12，正在尝试安装……"
      if command -v apt-get >/dev/null 2>&1; then
        if [[ "$(id -u)" -eq 0 ]]; then
          apt-get update
          apt-get install -y python3 python3-venv python3-pip
        elif command -v sudo >/dev/null 2>&1; then
          sudo apt-get update
          sudo apt-get install -y python3 python3-venv python3-pip
        else
          echo "请先安装 Python 3.10–3.12 和 python3-venv。" >&2
          return 1
        fi
      else
        echo "请先安装 Python 3.10–3.12。" >&2
        return 1
      fi
      ;;
    *)
      echo "当前系统请改用 启动同传.bat（Windows）或手动安装 Python 3.10–3.12。" >&2
      return 1
      ;;
  esac
  if found="$(find_python)"; then
    PYTHON="$found"
    return 0
  fi
  echo "已尝试安装，仍未找到可用的 Python 3.10–3.12。" >&2
  return 1
}

ensure_runtime() {
  echo "检测到系统：$(uname -s) $(uname -m)"
  ensure_python
  echo "使用 Python：$PYTHON"
  if [[ ! -x .venv/bin/python ]] || ! python_ok .venv/bin/python; then
    echo "正在创建本地 Python 环境……"
    rm -rf .venv
    "$PYTHON" -m venv .venv
  fi
  echo "正在安装应用依赖（首次需要联网，可能要几分钟）……"
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
  if ! .venv/bin/python setup_models.py; then
    echo "翻译模型暂未安装；识别仍可使用，安装模型后会显示中文译文。" >&2
  fi
}

ensure_cloudflared() {
  if command -v cloudflared >/dev/null 2>&1; then
    return 0
  fi
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "未找到 cloudflared。请先安装：https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/" >&2
    return 1
  fi
  echo "未找到 cloudflared，正在通过 Homebrew 安装……"
  ensure_brew
  brew install cloudflared
  if ! command -v cloudflared >/dev/null 2>&1; then
    echo "cloudflared 安装失败。" >&2
    return 1
  fi
}
