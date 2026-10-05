#!/usr/bin/env python3
"""The subtitle server must start when optional DeepSeek helpers are absent."""

from __future__ import annotations

import builtins
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

original_import = builtins.__import__


def without_deepseek(name, globals=None, locals=None, fromlist=(), level=0):
    if name in {"deepseek_api", "deepseek_hub"}:
        raise ModuleNotFoundError(f"No module named '{name}'", name=name)
    return original_import(name, globals, locals, fromlist, level)


builtins.__import__ = without_deepseek
try:
    import server
finally:
    builtins.__import__ = original_import

assert server.deepseek_api.available() is False
assert server.deepseek_hub.installed() is None
assert server.deepseek_hub.snapshot()["ready"] is False
assert server.installed_deepseek() is None
print("optional DeepSeek fallback ok")
