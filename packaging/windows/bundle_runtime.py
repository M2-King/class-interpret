#!/usr/bin/env python3
"""Put embeddable CPython + get-pip.py into DEST for the Windows zip."""
from __future__ import annotations

import os
import sys
import urllib.request
import zipfile
from pathlib import Path

DEST = Path(os.environ["DEST"])
CACHE = Path(os.environ.get("WIN_RUNTIME_CACHE", Path(__file__).resolve().parent / "cache"))
PY_NAME = "python-3.12.10-embed-amd64.zip"
PTH = (
    "python312.zip\r\n"
    ".\r\n"
    "Lib\\site-packages\r\n"
    "import site\r\n"
)
PY_URLS = (
    "https://mirrors.huaweicloud.com/python/3.12.10/" + PY_NAME,
    "https://cdn.npmmirror.com/binaries/python/3.12.10/" + PY_NAME,
    "https://www.python.org/ftp/python/3.12.10/" + PY_NAME,
)
PIP_URLS = (
    "https://mirrors.aliyun.com/pypi/get-pip.py",
    "https://bootstrap.pypa.io/get-pip.py",
)


def fetch(urls: tuple[str, ...], dest: Path, minimum: int) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size >= minimum:
        return
    last = None
    for url in urls:
        print("Downloading", url)
        try:
            urllib.request.urlretrieve(url, dest.with_suffix(dest.suffix + ".part"))
            part = dest.with_suffix(dest.suffix + ".part")
            if part.is_file() and part.stat().st_size >= minimum:
                part.replace(dest)
                return
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise SystemExit(f"Could not download {dest.name}: {last}")


def main() -> int:
    py_zip = CACHE / PY_NAME
    get_pip = CACHE / "get-pip.py"
    fetch(PY_URLS, py_zip, 1_000_000)
    fetch(PIP_URLS, get_pip, 10_000)
    runtime = DEST / ".runtime" / "python"
    if runtime.exists():
        for path in sorted(runtime.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            else:
                path.rmdir()
        runtime.rmdir()
    runtime.mkdir(parents=True)
    with zipfile.ZipFile(py_zip) as zf:
        zf.extractall(runtime)
    (runtime / "python312._pth").write_bytes(PTH.encode("ascii"))
    if not (runtime / "python.exe").is_file():
        raise SystemExit("embeddable python.exe missing after extract")
    (DEST / "get-pip.py").write_bytes(get_pip.read_bytes())
    print("Bundled", runtime / "python.exe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
