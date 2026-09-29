#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

ADDRESS="http://127.0.0.1:8765/"

# shellcheck source=bootstrap.sh
source ./bootstrap.sh
ensure_cloudflared

service_up() {
  curl -fsS --max-time 1 "${ADDRESS}api/status" >/dev/null 2>&1
}

if ! service_up; then
  echo "本地同传尚未运行，正在检测系统并安装依赖（首次可能需要几分钟）……"
  CLASS_INTERPRET_NO_BROWSER=1 bash start.sh >/tmp/class-interpret-start.log 2>&1 &
  ready=0
  for _ in $(seq 1 180); do
    if service_up; then
      ready=1
      break
    fi
    sleep 2
  done
  if [[ "$ready" -ne 1 ]]; then
    echo "本地服务未能在时限内启动。请查看 /tmp/class-interpret-start.log 或先双击 启动同传.command。" >&2
    exit 1
  fi
  echo "本地服务已就绪。"
fi

echo
echo "Mac 终端里接下来会打印一个 https 地址。"
echo "把该地址发到手机，用 Safari 或 Chrome 打开即可（不要用微信）。"
echo "识别仍在这台电脑上；下课后在本窗口按 Ctrl+C。"
echo "该地址在隧道开启期间任何人打开都能访问。"
echo

exec cloudflared tunnel --url http://127.0.0.1:8765
