#!/usr/bin/env python3
import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()
host, port = httpd.server_address
base = f"http://{host}:{port}"

with urllib.request.urlopen(base + "/api/status") as response:
    data = json.loads(response.read().decode())
assert data.get("version") == "0.3.0"
assert "translation" in data
assert "deepseek" in data
assert "deepseek_ready" in data
assert "ollama" in data
assert "whisper" in data
assert "whisper_models" in data

with urllib.request.urlopen(base + "/") as response:
    html = response.read().decode()
    assert "no-store" in (response.headers.get("Cache-Control") or "")
assert "setup_models.py" not in html
assert "0.3.0" in html
assert 'id="model-banner"' in html
assert "现在安装中文翻译模型" in html
assert "下载语音模型" in html
assert 'id="install-whisper"' in html
assert 'id="install-deepseek"' in html
assert "安装 DeepSeek" in html
assert 'id="deepseek-health"' in html
assert 'id="quit-app"' in html
assert "退出听课搭子" in html
assert "fff4cc" in Path(__file__).resolve().parents[1].joinpath("style.css").read_text(encoding="utf-8")

with urllib.request.urlopen(base + "/app.js?v=0.3.0") as response:
    script = response.read().decode()
assert "/api/translation/install" in script
assert "/api/whisper/install" in script
assert "/api/deepseek/install" in script
assert "/api/shutdown" in script
assert "AbortSignal.timeout" not in script
assert "modelBanner.classList.toggle" in script

req = urllib.request.Request(base + "/api/shutdown", data=b"", method="POST")
with urllib.request.urlopen(req) as response:
    payload = json.loads(response.read().decode())
assert payload["ok"] is True

httpd.server_close()
print("api ok")
