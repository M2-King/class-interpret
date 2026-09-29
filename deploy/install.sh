#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/class-interpret"
SERVICE_FILE="/etc/systemd/system/class-interpret.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "请使用 root 运行：sudo bash deploy/install.sh" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 Python 3。" >&2
  exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get install -y python3-venv
  else
    echo "请先安装 Python venv 模块。" >&2
    exit 1
  fi
fi

cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python setup_models.py
echo "正在预下载 Small 英语识别模型……"
.venv/bin/python -c 'from faster_whisper import WhisperModel; WhisperModel("small", device="cpu", compute_type="int8")'

install -m 0644 deploy/class-interpret.service "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable --now class-interpret.service
sleep 2
systemctl is-active --quiet class-interpret.service

echo "同传服务已启动，仅监听服务器本机 127.0.0.1:8765。"
echo "手机请建立 SSH 本地转发：127.0.0.1:8765 -> 服务器 127.0.0.1:8765"
