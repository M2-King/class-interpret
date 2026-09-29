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
assert "translation" in data
assert "deepseek" in data

with urllib.request.urlopen(base + "/") as response:
    html = response.read().decode()
assert "现在安装中文翻译模型" in html
assert "退出听课搭子" in html

with urllib.request.urlopen(base + "/app.js") as response:
    script = response.read().decode()
assert "/api/translation/install" in script
assert "/api/shutdown" in script

req = urllib.request.Request(base + "/api/shutdown", data=b"", method="POST")
with urllib.request.urlopen(req) as response:
    payload = json.loads(response.read().decode())
assert payload["ok"] is True

httpd.server_close()
print("api ok")
