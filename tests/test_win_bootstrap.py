#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
import win_bootstrap as wb

assert wb.VERSION_FALLBACK == "0.3.3"
assert any("tuna.tsinghua" in url for url in wb.PIP_INDEXES)
assert any("aliyun" in url for url in wb.PIP_INDEXES)

assert wb.is_temp_path(r"C:\Users\a\AppData\Local\Temp\Temp1_x\ClassInterpreter-0.3.3")
assert wb.is_temp_path(r"C:\Users\a\AppData\Local\Temp\7zO123\ClassInterpreter-0.3.3")
assert not wb.is_temp_path(r"C:\Users\a\Downloads\ClassInterpreter-0.3.3")
assert not wb.is_temp_path(r"D:\class-interpret")

venv_root = Path("/tmp/ci-fake-win")
(venv_root / ".venv" / "Scripts").mkdir(parents=True, exist_ok=True)
(venv_root / ".runtime" / "python").mkdir(parents=True, exist_ok=True)
(venv_root / ".venv" / "Scripts" / "python.exe").write_bytes(b"x" * 5000)
(venv_root / ".runtime" / "python" / "python.exe").write_bytes(b"y" * 5000)
chosen = wb.choose_python(venv_root)
assert str(chosen).replace("\\", "/").endswith(".venv/Scripts/python.exe"), chosen

only_bundle = Path("/tmp/ci-fake-win-bundle")
(only_bundle / ".runtime" / "python").mkdir(parents=True, exist_ok=True)
(only_bundle / ".runtime" / "python" / "python.exe").write_bytes(b"y" * 5000)
chosen = wb.choose_python(only_bundle)
assert str(chosen).replace("\\", "/").endswith(".runtime/python/python.exe"), chosen

assert wb.choose_python(Path("/tmp/ci-fake-win-empty")) is None

src = (root / "win_bootstrap.py").read_text(encoding="utf-8")
assert "HF_ENDPOINT" in src
assert "hf-mirror.com" in src
assert "server.py" in src
assert "get-pip.py" in src
print("win_bootstrap ok")
