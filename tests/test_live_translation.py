#!/usr/bin/env python3
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server

entry = {
    "id": "entry-1",
    "at": 1.0,
    "en": "forming the truth table",
    "zh": "",
    "translation_status": "pending",
}
stored_session = {"id": "a" * 32, "entries": [copy.deepcopy(entry)]}


def read_session(_session_id):
    return copy.deepcopy(stored_session)


def save_session(session):
    stored_session.clear()
    stored_session.update(copy.deepcopy(session))


server.read_session = read_session
server.save_session = save_session
server.translate = lambda _text: "构建真值表（本地）"
server.deepseek_api.available = lambda: True
server.translation_hub.cloud_translation = lambda *args, **kwargs: "构建真值表"

updates = list(server.translate_live_entry(entry, {
    "session_id": "a" * 32,
    "glossary": "truth table=真值表",
}))
assert [item["translation_status"] for item in updates] == ["provisional", "final"]
assert updates[0]["zh"] == "构建真值表（本地）"
assert updates[1]["zh"] == "构建真值表"
assert stored_session["entries"][0]["translation_status"] == "final"
print("live_translation ok")
