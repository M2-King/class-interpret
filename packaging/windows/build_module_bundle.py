#!/usr/bin/env python3
"""Build a fallback zip of pure-Python application helpers for Windows."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path


MODULES = (
    "deepseek_api.py",
    "deepseek_hub.py",
    "secret_box.py",
    "setup_deepseek.py",
    "setup_models.py",
    "setup_whisper.py",
    "ssl_certs.py",
    "streaming_hub.py",
    "streaming_server.py",
    "translation_hub.py",
    "whisper_hub.py",
)


def build(root: Path, output: Path) -> None:
    missing = [name for name in MODULES if not (root / name).is_file()]
    if missing:
        raise SystemExit("Missing Windows application modules: " + ", ".join(missing))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in MODULES:
            bundle.write(root / name, name)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_module_bundle.py ROOT OUTPUT")
    build(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
