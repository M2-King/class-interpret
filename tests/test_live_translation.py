#!/usr/bin/env python3
import copy
import sys
import time
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
server.translate = lambda _text, **_kwargs: "构建真值表（本地）"
server.deepseek_api.available = lambda: True


def delayed_cloud(*args, **kwargs):
    time.sleep(0.05)
    return "构建真值表"


server.translation_hub.cloud_translation = delayed_cloud

updates = list(server.translate_live_entry(entry, {
    "session_id": "a" * 32,
    "glossary": "truth table=真值表",
}))
assert [item["translation_status"] for item in updates] == ["provisional", "final"]
assert updates[0]["zh"] == "构建真值表（本地）"
assert updates[1]["zh"] == "构建真值表"
assert stored_session["entries"][0]["translation_status"] == "final"


def slow_offline(_text, **_kwargs):
    time.sleep(0.1)
    return "不应覆盖云端结果"


server.translate = slow_offline
server.translation_hub.cloud_translation = lambda *args, **kwargs: "云端先返回"
stored_session["entries"] = [copy.deepcopy(entry)]
cloud_first = list(server.translate_live_entry(entry, {
    "session_id": "a" * 32,
    "glossary": "truth table=真值表",
}))
assert len(cloud_first) == 1
assert cloud_first[0]["zh"] == "云端先返回"
assert cloud_first[0]["translation_status"] == "final"

server.deepseek_api.available = lambda: False
server.translate = lambda _text, **_kwargs: "仅离线翻译"
stored_session["entries"] = [copy.deepcopy(entry)]
offline_only = list(server.translate_live_entry(entry, {
    "session_id": "a" * 32,
    "glossary": "",
}))
assert len(offline_only) == 1
assert offline_only[0]["zh"] == "仅离线翻译"
assert offline_only[0]["translation_status"] == "offline"
print("live_translation ok")
