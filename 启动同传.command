#!/bin/bash
cd "$(dirname "$0")"
bash start.sh
status=$?
if [[ $status -ne 0 && $status -ne 130 && $status -ne 143 ]]; then
  echo
  echo "启动失败。请查看上方提示。"
  read -r -p "按回车键关闭窗口…"
fi
