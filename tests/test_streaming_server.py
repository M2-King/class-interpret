#!/usr/bin/env python3
import json
import socket
import sys
import threading
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / ".test-deps"))
sys.path.insert(0, str(root))

try:
    from websockets.sync.client import connect
except ImportError:
    print("streaming_server skipped (install requirements.txt to run transport integration)")
    raise SystemExit(0)

from streaming_server import StreamingServer

with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]

saved = []
translated = threading.Event()


def decode(job, settings):
    assert settings["session_id"] == "a" * 32
    return "forming the truth table"


def save(job, text, settings):
    entry = {"id": "entry-1", "at": job.elapsed, "en": text, "zh": "", "translation_status": "pending"}
    saved.append(entry)
    return entry


def translate(entry, settings):
    translated.set()
    return {**entry, "zh": "构建真值表", "translation_status": "final"}


service = StreamingServer("127.0.0.1", port, decode, save, translate)
service.start()
assert service.ready, service.error

events = []
with connect(service.config()["url"], open_timeout=3) as websocket:
    websocket.send(json.dumps({
        "type": "start",
        "token": service.config()["token"],
        "session_id": "a" * 32,
        "model": "small",
        "base_elapsed": 2,
    }))
    ready = json.loads(websocket.recv(timeout=3))
    assert ready["type"] == "ready"
    websocket.send((9000).to_bytes(2, "little", signed=True) * 8000)
    websocket.send(json.dumps({"type": "commit", "elapsed": 2.5}))
    websocket.send(json.dumps({"type": "stop", "elapsed": 2.5}))
    while True:
        event = json.loads(websocket.recv(timeout=5))
        events.append(event)
        if event["type"] == "ready_to_stop":
            break

assert saved and saved[0]["at"] == 2.5
assert any(event["type"] == "final" for event in events)
assert translated.wait(2)
service.stop()
print("streaming_server ok")
