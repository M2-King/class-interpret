#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import whisper_hub

whisper_hub.configure()
assert whisper_hub.cached_models()["small"] is False
text = whisper_hub.friendly_error(TimeoutError("ConnectTimeout: [Errno 60] Operation timed out on the Hub"))
assert "手机热点" in text
assert "setup_models.py" not in text
print("whisper_hub ok")
