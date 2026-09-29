#!/usr/bin/env python3
import io
import json
import sys
import tarfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deepseek_hub

assert deepseek_hub.pick_model([]) is None
assert deepseek_hub.pick_model(["llama3:8b"]) is None
assert deepseek_hub.pick_model(["deepseek-r1:1.5b"]) == "deepseek-r1:1.5b"
assert deepseek_hub.pick_model(["deepseek-r1:1.5b", "deepseek-r1:7b"]) == "deepseek-r1:7b"
assert deepseek_hub.pick_model(["deepseek-r1:8b", "deepseek-r1:7b"]) == "deepseek-r1:8b"
assert deepseek_hub.normalize_model(None) == "deepseek-r1:1.5b"
assert deepseek_hub.normalize_model("deepseek-r1:7b") == "deepseek-r1:7b"
try:
    deepseek_hub.normalize_model("gpt-4")
    raise SystemExit("expected invalid model")
except ValueError:
    pass

text = deepseek_hub.friendly_error(TimeoutError("timed out connecting to registry.ollama.ai"))
assert "手机热点" in text
assert "DeepSeek" in text or "Ollama" in text

tmp = Path("/tmp/class-interpret-ollama-test")
if tmp.exists():
    import shutil
    shutil.rmtree(tmp)
tmp.mkdir(parents=True)

exe_name = "ollama.exe" if sys.platform == "win32" else "ollama"
payload = b"#!/bin/sh\necho ollama\n"
zip_path = tmp / "ollama.zip"
with zipfile.ZipFile(zip_path, "w") as zf:
    zf.writestr(f"bin/{exe_name}", payload)
dest = tmp / "from-zip"
found = deepseek_hub.extract_archive(zip_path, dest)
assert found.name == exe_name, found
assert found.is_file()

tgz_path = tmp / "ollama.tgz"
with tarfile.open(tgz_path, "w:gz") as tar:
    info = tarfile.TarInfo(name=exe_name)
    info.size = len(payload)
    tar.addfile(info, io.BytesIO(payload))
dest2 = tmp / "from-tgz"
found = deepseek_hub.extract_archive(tgz_path, dest2)
assert found.name == exe_name

darwin = [url for url in deepseek_hub.archive_urls("darwin", "arm64") if url.endswith("ollama-darwin.tgz")]
assert darwin, deepseek_hub.archive_urls("darwin", "arm64")
windows = [url for url in deepseek_hub.archive_urls("win32", "AMD64") if "ollama-windows-amd64.zip" in url]
assert windows, deepseek_hub.archive_urls("win32", "AMD64")

print("deepseek_hub ok")
