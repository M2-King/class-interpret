#!/usr/bin/env python3
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

fake = types.ModuleType("deepseek_api")
fake.available = lambda: False
fake.chat = lambda prompt, timeout=0: "真值表"
sys.modules["deepseek_api"] = fake

import translation_hub

assert translation_hub.validate_translation("truth table", "真值表") == "真值表"
assert translation_hub.validate_translation("truth table", "译文：真值表") == "真值表"

bad = [
    r"{\fn黑体\fs22\bord1} 真值表",
    "<script>alert(1)</script>真值表",
    "English only",
    "真值表" * 500,
]
for value in bad:
    try:
        translation_hub.validate_translation("truth table", value)
        raise AssertionError(f"expected rejection: {value[:30]}")
    except translation_hub.TranslationRejected:
        pass

text, provider, quality = translation_hub.best_translation(
    "truth table", lambda value: "真值表", prefer_cloud=False
)
assert (text, provider, quality) == ("真值表", "argos", "offline")

fake.available = lambda: True
text, provider, quality = translation_hub.best_translation("truth table", lambda value: "错误")
assert (text, provider, quality) == ("真值表", "deepseek", "final")

print("translation_hub ok")
