"""Download the free offline English-to-Chinese translation model once."""

from __future__ import annotations

import importlib
import subprocess
import sys
from collections.abc import Callable
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


ProgressCallback = Callable[[int, str, str], None]


def _progress(callback: ProgressCallback | None, percent: int, phase: str, detail: str) -> None:
    if callback:
        callback(percent, phase, detail)


def ensure_argos(progress: ProgressCallback | None = None) -> None:
    try:
        _import_argos()
        _progress(progress, 38, "Translation engine ready", "Using the existing Argos translation engine.")
        return
    except ImportError:
        pass

    ssl_certs.apply()
    req = ROOT / "requirements.txt"
    packages = ["-r", str(req)] if req.is_file() else ["argostranslate"]
    ok = False
    for index, host in PIP_INDEXES:
        _progress(progress, 12, "Installing translation engine", f"Connecting to {host}...")
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


def main(progress: ProgressCallback | None = None) -> None:
    ssl_certs.apply()
    _progress(progress, 5, "Preparing translation", "Checking the English to Chinese translation engine...")
    ensure_argos(progress)
    package, translate = _import_argos()

    languages = {language.code: language for language in translate.get_installed_languages()}
    if "en" in languages and "zh" in languages:
        if languages["en"].get_translation(languages["zh"]):
            print("英语 → 中文翻译模型已安装。")
            _progress(progress, 100, "Translation ready", "English to Chinese translation is installed.")
            return

    _progress(progress, 48, "Checking translation model", "Downloading the Argos model catalogue...")
    print("正在获取免费的 Argos 翻译模型索引……")
    package.update_package_index()
    packages = package.get_available_packages()
    match = next((p for p in packages if p.from_code == "en" and p.to_code == "zh"), None)
    if match is None:
        raise SystemExit("模型索引里没有 en → zh 模型；请稍后重试。")
    _progress(progress, 60, "Downloading translation model", "Downloading the English to Chinese language pack...")
    print("正在下载并安装英语 → 中文模型……")
    downloaded = match.download()
    _progress(progress, 88, "Installing translation model", "Unpacking and registering the language pack...")
    package.install_from_path(downloaded)
    _progress(progress, 100, "Translation ready", "English to Chinese translation is installed.")
    print("翻译模型安装完成。")


if __name__ == "__main__":
    main()
