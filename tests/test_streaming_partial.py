#!/usr/bin/env python3
import json
import sys
import threading
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from streaming_server import StreamingServer


def decode(_job, _settings):
    return "forming the truth table"


def save(job, text, _settings):
    return {"id": "entry-1", "at": job.elapsed, "en": text, "zh": "", "translation_status": "pending"}


def translate_final(entry, _settings):
    return {**entry, "zh": "构建真值表", "translation_status": "final"}


def translate_partial(text, _settings):
    assert text == "forming the truth table"
    return "正在构建真值表"


service = StreamingServer("127.0.0.1", 0, decode, save, translate_final, translate_partial)


class FakeConnection:
    def __init__(self):
        self.sent = []
        self.lock = threading.Lock()

    def recv(self, timeout=0):
        return json.dumps({
            "type": "start",
            "token": service.token,
            "session_id": "a" * 32,
            "model": "small",
            "base_elapsed": 0,
        })

    def send(self, payload):
        with self.lock:
            self.sent.append(json.loads(payload))

    def close(self, **_kwargs):
        return None

    def has(self, kind):
        with self.lock:
            return any(item.get("type") == kind for item in self.sent)

    def __iter__(self):
        yield (9000).to_bytes(2, "little", signed=True) * 16000
        deadline = time.monotonic() + 3
        while not self.has("partial_translation") and time.monotonic() < deadline:
            time.sleep(0.01)
        yield json.dumps({"type": "commit", "elapsed": 1.0})
        yield json.dumps({"type": "stop", "elapsed": 1.0})


connection = FakeConnection()
service._handle(connection)
assert connection.has("partial")
assert connection.has("partial_translation")
preview = next(item for item in connection.sent if item.get("type") == "partial_translation")
assert preview["text"] == "forming the truth table"
assert preview["zh"] == "正在构建真值表"
assert preview["translation_status"] == "provisional"
print("streaming_partial ok")
