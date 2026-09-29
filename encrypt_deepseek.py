#!/usr/bin/env python3
"""Encrypt secrets/deepseek.api into deepseek_api.enc for the shared zip."""

from __future__ import annotations

from pathlib import Path

import deepseek_api

ROOT = Path(__file__).resolve().parent
PLAIN = ROOT / "secrets" / "deepseek.api"
ENC = ROOT / "deepseek_api.enc"


def main() -> None:
    if not PLAIN.is_file():
        raise SystemExit("缺少 secrets/deepseek.api，请把 DeepSeek API key 贴进这个文件。")
    deepseek_api.seal_from_plaintext(PLAIN, ENC)
    print("已写入加密文件 deepseek_api.enc（明文 key 不会打进zip）。")


if __name__ == "__main__":
    main()
