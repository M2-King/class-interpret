#!/usr/bin/env python3
import json
import os
import sys
from io import BytesIO
from pathlib import Path
from urllib import error, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deepseek_api
import secret_box

text = """
# comment
sk-live-example-key
"""
assert deepseek_api.parse_plaintext(text) == "sk-live-example-key"
assert deepseek_api.parse_plaintext("# only comments\n") is None

os.environ["CLASS_INTERPRET_DEEPSEEK_API"] = "sk-from-env"
assert deepseek_api.load_key() == "sk-from-env"
del os.environ["CLASS_INTERPRET_DEEPSEEK_API"]

tmp = Path("/tmp/class-interpret-deepseek-api-test")
tmp.mkdir(exist_ok=True)
plain = tmp / "deepseek.api"
enc = tmp / "deepseek_api.enc"
plain.write_text("# paste\nsk-file-key-please\n", encoding="utf-8")
deepseek_api.seal_from_plaintext(plain, enc)
assert enc.is_file()
blob = enc.read_bytes()
assert b"sk-file" not in blob
assert secret_box.unseal(blob) == "sk-file-key-please"
assert deepseek_api.load_key(root=tmp) == "sk-file-key-please"

calls = []

class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode()
    def read(self):
        return self._payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

def fake_urlopen(req, timeout=0, context=None):
    calls.append({"url": req.full_url, "auth": req.headers.get("Authorization") or req.get_header("Authorization")})
    return FakeResponse({"choices": [{"message": {"content": "课堂要点：回归。"}}]})

request.urlopen = fake_urlopen  # type: ignore
out = deepseek_api.chat("总结这一课", key="sk-file-key-please")
assert "回归" in out
assert calls and "api.deepseek.com" in calls[0]["url"]
assert "sk-file-key-please" in (calls[0]["auth"] or "")

print("deepseek_api ok")
