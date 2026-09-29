#!/usr/bin/env python3
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

calls: list[dict] = []


class FakeWhisperModel:
    fail_cuda = False

    def __init__(self, name, device="cpu", compute_type=None, local_files_only=False):
        calls.append({
            "name": name,
            "device": device,
            "compute_type": compute_type,
            "local_files_only": local_files_only,
        })
        if device == "cuda" and FakeWhisperModel.fail_cuda:
            raise RuntimeError("CUDA is not available")
        self.name = name
        self.device = device


fake = types.ModuleType("faster_whisper")
fake.WhisperModel = FakeWhisperModel
sys.modules["faster_whisper"] = fake

import whisper_hub

whisper_hub.configure()
assert whisper_hub.cached_models()["small"] is False
text = whisper_hub.friendly_error(TimeoutError("ConnectTimeout: [Errno 60] Operation timed out on the Hub"))
assert "手机热点" in text
assert "setup_models.py" not in text

whisper_hub.cached = lambda name: True

calls.clear()
FakeWhisperModel.fail_cuda = False
model, device = whisper_hub.create_model("small")
assert device == "GPU", device
assert [item["device"] for item in calls] == ["cuda"]
assert calls[0]["compute_type"] == "int8_float16"
assert calls[0]["local_files_only"] is True
assert calls[0]["name"] == "small"

calls.clear()
FakeWhisperModel.fail_cuda = True
model, device = whisper_hub.create_model("medium")
assert device == "CPU", device
assert [item["device"] for item in calls] == ["cuda", "cpu"]
assert calls[1]["compute_type"] == "int8"
assert calls[1]["local_files_only"] is True

calls.clear()
FakeWhisperModel.fail_cuda = False
model, device = whisper_hub.create_model("small", force_cpu=True)
assert device == "CPU", device
assert [item["device"] for item in calls] == ["cpu"]
assert calls[0]["local_files_only"] is True

print("whisper_hub ok")
