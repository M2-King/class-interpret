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

nested = Path("/tmp/ci-nested-extract/ClassInterpreter-0.3.3")
(nested.parent / ".venv" / "Scripts").mkdir(parents=True, exist_ok=True)
(nested / ".runtime" / "python").mkdir(parents=True, exist_ok=True)
(nested.parent / ".venv" / "Scripts" / "python.exe").write_bytes(b"v" * 5000)
(nested / ".runtime" / "python" / "python.exe").write_bytes(b"b" * 5000)
(nested.parent / "hf").mkdir(parents=True, exist_ok=True)
(nested.parent / "data").mkdir(parents=True, exist_ok=True)
chosen = wb.choose_python(nested)
assert ".venv/Scripts/python.exe" in str(chosen).replace("\\", "/"), chosen
assert "ClassInterpreter-0.3.3" not in str(chosen).replace("\\", "/")
import os
os.environ.pop("CLASS_INTERPRET_HF", None)
os.environ.pop("CLASS_INTERPRET_DATA", None)
wb.configure_env(nested)
assert os.environ["CLASS_INTERPRET_HF"].replace("\\", "/").endswith("/ci-nested-extract/hf")
assert os.environ["CLASS_INTERPRET_DATA"].replace("\\", "/").endswith("/ci-nested-extract/data")

embed = Path("/tmp/ci-embed-pth/.runtime/python")
embed.mkdir(parents=True, exist_ok=True)
(embed / "python312.zip").write_bytes(b"x")
(embed / "python312._pth").write_bytes(b"python312.zip\r\n.\r\n")
(embed / "python.exe").write_bytes(b"e" * 5000)
wb.enable_embed_site(str(embed / "python.exe"))
pth = (embed / "python312._pth").read_text(encoding="ascii")
assert "import site" in pth
assert "Lib\\site-packages" in pth

src = (root / "win_bootstrap.py").read_text(encoding="utf-8")
assert "HF_ENDPOINT" in src
assert "hf-mirror.com" in src
assert "server.py" in src
assert "get-pip.py" in src
assert "def stop_listener" in src
assert "def find_venv_root" in src
assert "def enable_embed_site" in src
assert "import site" in src
assert "pip.pyz" in src
assert "api/shutdown" in src
assert src.index("stop_listener") < src.index('["server.py"]')
wb.stop_listener(port=9, wait=0)
print("win_bootstrap ok")
