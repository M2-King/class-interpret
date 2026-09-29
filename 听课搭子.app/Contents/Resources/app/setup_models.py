"""Download the free offline English-to-Chinese translation model once."""

from __future__ import annotations

import ssl_certs


def main() -> None:
    ssl_certs.apply()
    try:
        import argostranslate.package
        import argostranslate.translate
    except ImportError:
        raise SystemExit("请先安装 requirements.txt 中的依赖。")

    languages = {language.code: language for language in argostranslate.translate.get_installed_languages()}
    if "en" in languages and "zh" in languages:
        if languages["en"].get_translation(languages["zh"]):
            print("英语 → 中文翻译模型已安装。")
            return

    print("正在获取免费的 Argos 翻译模型索引……")
    argostranslate.package.update_package_index()
    packages = argostranslate.package.get_available_packages()
    match = next((p for p in packages if p.from_code == "en" and p.to_code == "zh"), None)
    if match is None:
        raise SystemExit("模型索引里没有 en → zh 模型；请稍后重试。")
    print("正在下载并安装英语 → 中文模型……")
    argostranslate.package.install_from_path(match.download())
    print("翻译模型安装完成。")


if __name__ == "__main__":
    main()
