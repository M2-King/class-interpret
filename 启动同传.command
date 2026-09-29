#!/bin/bash
cd "$(dirname "$0")"
echo "正在检测系统并安装依赖。首次可能要几分钟，并可能要求输入 Mac 登录密码。"
echo "手机不需要操作这一步。"
echo
bash start.sh
status=$?
if [[ $status -ne 0 && $status -ne 130 && $status -ne 143 ]]; then
  echo
  echo "启动失败。请查看上方提示。"
  read -r -p "按回车键关闭窗口…"
fi
