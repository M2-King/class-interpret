#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
text = (root / "setup_models.py").read_text(encoding="utf-8")
assert "argostranslate" in text
assert "importlib.invalidate_caches" in text
assert "-m" in text and "pip" in text
assert "tuna.tsinghua" in text
assert "aliyun" in text
assert "Start.bat" in text or "Open.command" in text

js = (root / "app.js").read_text(encoding="utf-8")
assert "翻译模型安装失败：${message}。可改用手机热点后重试。" not in js
assert "translationFailNotice" in js
print("setup_models ok")
