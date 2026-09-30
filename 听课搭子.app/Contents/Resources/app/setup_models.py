"""Download the free offline English-to-Chinese translation model once."""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import ssl_certs

ROOT = Path(__file__).resolve().parent
PIP_INDEXES = (
    ("https://pypi.tuna.tsinghua.edu.cn/simple", "pypi.tuna.tsinghua.edu.cn"),
    ("https://mirrors.aliyun.com/pypi/simple", "mirrors.aliyun.com"),
    ("https://pypi.org/simple", "pypi.org"),
)


def _import_argos():
    import argostranslate.package
    import argostranslate.translate

    return argostranslate.package, argostranslate.translate


def ensure_argos() -> None:
    try:
        _import_argos()
        return
    except ImportError:
        pass

    ssl_certs.apply()
    req = ROOT / "requirements.txt"
    packages = ["-r", str(req)] if req.is_file() else ["argostranslate"]
    ok = False
    for index, host in PIP_INDEXES:
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--retries", "1", "--timeout", "45",
            "--index-url", index, "--trusted-host", host,
            *packages,
        ]
        print("正在安装翻译依赖：", " ".join(cmd[3:]))
        if subprocess.run(cmd, check=False).returncode == 0:
            ok = True
            break
    if not ok:
        raise SystemExit(
            "缺少 argostranslate。请换手机热点，关掉这个页面，重新双击 Start.bat 或 Open.command，等黑窗口装完依赖后再点黄色按钮。"
        )
    importlib.invalidate_caches()
    try:
        _import_argos()
    except ImportError:
        raise SystemExit(
            "依赖装完后仍无法导入 argostranslate。请关掉页面，重新双击 Start.bat / Open.command。"
        )


def main() -> None:
    ssl_certs.apply()
    ensure_argos()
    package, translate = _import_argos()

    languages = {language.code: language for language in translate.get_installed_languages()}
    if "en" in languages and "zh" in languages:
        if languages["en"].get_translation(languages["zh"]):
            print("英语 → 中文翻译模型已安装。")
            return

    print("正在获取免费的 Argos 翻译模型索引……")
    package.update_package_index()
    packages = package.get_available_packages()
    match = next((p for p in packages if p.from_code == "en" and p.to_code == "zh"), None)
    if match is None:
        raise SystemExit("模型索引里没有 en → zh 模型；请稍后重试。")
    print("正在下载并安装英语 → 中文模型……")
    package.install_from_path(match.download())
    print("翻译模型安装完成。")


if __name__ == "__main__":
    main()
