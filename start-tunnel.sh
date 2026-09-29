#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

ADDRESS="http://127.0.0.1:8765/"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "未找到 cloudflared。Mac 请先安装 Homebrew，再运行：brew install cloudflared" >&2
  echo "Windows / Linux 可从 https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/ 安装。" >&2
  exit 1
fi

if ! python3 -c "import urllib.request; urllib.request.urlopen('${ADDRESS}api/status', timeout=1)" >/dev/null 2>&1; then
  echo "本地同传尚未运行，正在启动（首次安装依赖可能需要几分钟）……"
  CLASS_INTERPRET_NO_BROWSER=1 bash start.sh >/tmp/class-interpret-start.log 2>&1 &
  ready=0
  for _ in $(seq 1 180); do
    if python3 -c "import urllib.request; urllib.request.urlopen('${ADDRESS}api/status', timeout=1)" >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 2
  done
  if [[ "$ready" -ne 1 ]]; then
    echo "本地服务未能在时限内启动。请查看 /tmp/class-interpret-start.log 或先运行 bash start.sh。" >&2
    exit 1
  fi
  echo "本地服务已就绪。"
fi

echo
echo "即将生成一个 https 地址。手机浏览器打开该地址即可录音（麦克风需要 HTTPS）。"
echo "识别仍在这台电脑上；电脑关机或结束此命令后手机不能继续用。"
echo "该地址在隧道开启期间任何人打开都能访问，课程结束后按 Ctrl+C 关闭。"
echo

exec cloudflared tunnel --url http://127.0.0.1:8765
