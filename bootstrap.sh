#!/usr/bin/env bash
# Shared by start.sh and start-tunnel.sh. Detects OS and installs missing runtimes.

CLASS_INTERPRET_PORT="${CLASS_INTERPRET_PORT:-8765}"

service_up() {
  local address="${1:-http://127.0.0.1:${CLASS_INTERPRET_PORT}/}"
  curl -fsS --max-time 1 "${address}api/status" >/dev/null 2>&1
}

app_version() {
  local file=${1:-}
  if [[ -n "$file" && -f "$file" ]]; then
    tr -d '[:space:]' < "$file"
  elif [[ -f VERSION ]]; then
    tr -d '[:space:]' < VERSION
  else
    printf '%s' "0.2.2"
  fi
}

version_matches() {
  local wanted=$1
  local address="${2:-http://127.0.0.1:${CLASS_INTERPRET_PORT}/}"
  local body
  body="$(curl -fsS --max-time 1 "${address}api/status" 2>/dev/null || true)"
  [[ -n "$wanted" && "$body" == *"\"version\": \"$wanted\""* ]]
}

stop_existing_server() {
  local port="${1:-$CLASS_INTERPRET_PORT}"
  local pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  fi
  if [[ -n "$pids" ]]; then
    echo "正在停止旧的听课搭子进程（端口 $port）……"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 1
    # shellcheck disable=SC2086
    kill -9 $pids 2>/dev/null || true
  fi
}

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

install_python_macos_pkg() {
  local pkg="/tmp/class-interpret-python3.12.pkg"
  local url="https://www.python.org/ftp/python/3.12.7/python-3.12.7-macos11.pkg"
  echo "正在下载官方 Python 3.12 安装包……"
  curl -fL --retry 3 -o "$pkg" "$url"
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "do shell script \"installer -pkg '$pkg' -target /\" with administrator privileges"
  else
    sudo installer -pkg "$pkg" -target /
  fi
}

ensure_python() {
  local found
  export PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:/Library/Frameworks/Python.framework/Versions/3.11/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
  if found="$(find_python)"; then
    PYTHON="$found"
    return 0
  fi
  case "$(uname -s)" in
    Darwin)
      echo "未找到 Python 3.10–3.12，正在安装官方 Python（会弹出 Mac 密码窗口，不是终端命令）……"
      if ! install_python_macos_pkg; then
        echo "官方安装包失败，改用 Homebrew……"
        ensure_brew
        brew install python@3.12
      fi
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

export_macos_certs() {
  [[ "$(uname -s)" == Darwin ]] || return 0
  local bundle="${CLASS_INTERPRET_CERTS:-}"
  if [[ -z "$bundle" ]]; then
    if [[ -n "${CLASS_INTERPRET_VENV:-}" ]]; then
      bundle="$(dirname "$CLASS_INTERPRET_VENV")/certs.pem"
    else
      bundle="$(pwd)/certs.pem"
    fi
  fi
  mkdir -p "$(dirname "$bundle")"
  : > "$bundle"
  local kc
  for kc in \
    "/System/Library/Keychains/SystemRootCertificates.keychain" \
    "/Library/Keychains/System.keychain" \
    "$HOME/Library/Keychains/login.keychain-db" \
    "$HOME/Library/Keychains/login.keychain"; do
    if [[ -e "$kc" ]]; then
      security find-certificate -a -p "$kc" >> "$bundle" 2>/dev/null || true
    fi
  done
  if [[ ! -s "$bundle" && -f /etc/ssl/cert.pem ]]; then
    cat /etc/ssl/cert.pem > "$bundle"
  fi
  if [[ -s "$bundle" ]]; then
    export SSL_CERT_FILE="$bundle"
    export REQUESTS_CA_BUNDLE="$bundle"
    export CURL_CA_BUNDLE="$bundle"
    export PIP_CERT="$bundle"
    echo "已使用 macOS 钥匙串证书：$bundle"
  fi
}

pip_with_ssl_fallback() {
  local py=$1
  shift
  if "$py" -m pip --retries 1 --timeout 30 "$@"; then
    return 0
  fi
  echo "pip 证书校验失败，改用 trusted-host 重试……"
  "$py" -m pip --retries 1 --timeout 30 --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org "$@"
}

ensure_venv_module() {
  if "$PYTHON" -c 'import ensurepip, venv' >/dev/null 2>&1; then
    return 0
  fi
  if [[ "$(uname -s)" != "Linux" ]] || ! command -v apt-get >/dev/null 2>&1; then
    echo "当前 Python 无法创建虚拟环境。请安装 venv（Debian/Ubuntu：python3-venv）。" >&2
    return 1
  fi
  local series
  series="$("$PYTHON" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
  echo "正在安装 python${series}-venv（创建虚拟环境需要它）……"
  if [[ "$(id -u)" -eq 0 ]]; then
    apt-get update
    apt-get install -y "python${series}-venv" python3-venv || apt-get install -y python3-venv
  elif command -v sudo >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y "python${series}-venv" python3-venv || sudo apt-get install -y python3-venv
  else
    echo "请先安装 python${series}-venv。" >&2
    return 1
  fi
}

ensure_runtime() {
  local venv="${CLASS_INTERPRET_VENV:-.venv}"
  echo "检测到系统：$(uname -s) $(uname -m)"
  ensure_python
  echo "使用 Python：$PYTHON"
  export_macos_certs
  ensure_venv_module
  if [[ ! -x "$venv/bin/python" ]] || ! python_ok "$venv/bin/python"; then
    echo "正在创建本地 Python 环境……"
    rm -rf "$venv"
    "$PYTHON" -m venv "$venv"
  fi
  echo "正在安装应用依赖（首次需要联网，可能要几分钟）……"
  export PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-30}"
  pip_with_ssl_fallback "$venv/bin/python" install --upgrade pip
  pip_with_ssl_fallback "$venv/bin/python" install certifi
  pip_with_ssl_fallback "$venv/bin/python" install -r requirements.txt
  if ! "$venv/bin/python" setup_models.py; then
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
