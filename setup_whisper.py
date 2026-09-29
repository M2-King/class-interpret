"""Download the default local Whisper speech model (Small)."""

from __future__ import annotations

import sys

import ssl_certs
import whisper_hub


def main(name: str = "small") -> None:
    ssl_certs.apply()
    whisper_hub.configure()
    whisper_hub.download(name)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "small")
