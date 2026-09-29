"""Download the local DeepSeek-R1 model through Ollama (default 1.5b)."""

from __future__ import annotations

import sys

import deepseek_hub
import ssl_certs


def main(name: str = deepseek_hub.DEFAULT_MODEL) -> None:
    ssl_certs.apply()
    ready = deepseek_hub.install(name)
    print(f"DeepSeek 已就绪：{ready}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else deepseek_hub.DEFAULT_MODEL)
