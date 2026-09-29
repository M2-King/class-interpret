"""Windows first-launch helper. Stdlib only. Prefer an existing .venv, else bundled Python."""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

VERSION_FALLBACK = "0.3.3"
PIP_INDEXES = (
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://mirrors.aliyun.com/pypi/simple",
    "https://pypi.org/simple",
)
PIP_TRUSTED = (
    "pypi.tuna.tsinghua.edu.cn",
    "mirrors.aliyun.com",
    "pypi.org",
    "files.pythonhosted.org",
    "pypi.python.org",
)


def is_temp_path(path: str) -> bool:
    text = str(path or "").replace("/", "\\")
    low = text.lower()
    if "\\appdata\\local\\temp\\" in low:
        return True
    for key in ("TEMP", "TMP"):
        raw = os.environ.get(key)
        if not raw:
            continue
        prefix = str(Path(raw)).replace("/", "\\").rstrip("\\").lower()
        if prefix and (low == prefix or low.startswith(prefix + "\\")):
            return True
    return False


def choose_python(root: Path) -> Path | None:
    candidates = (
        root / ".venv" / "Scripts" / "python.exe",
        root / ".runtime" / "python" / "python.exe",
    )
    for exe in candidates:
        try:
            if exe.is_file() and exe.stat().st_size >= 4096:
                return exe
        except OSError:
            continue
    return None


def log(message: str) -> None:
    print(message, flush=True)


def run(exe: str, args: list[str]) -> int:
    completed = subprocess.run([exe, *args], check=False)
    return int(completed.returncode or 0)


def pip_ok(exe: str) -> bool:
    return run(exe, ["-m", "pip", "--version"]) == 0


def packages_ok(exe: str) -> bool:
    return run(exe, ["-c", "import faster_whisper, argostranslate"]) == 0


def ensure_pip(root: Path, exe: str) -> None:
    if pip_ok(exe):
        return
    get_pip = root / "get-pip.py"
    if not get_pip.is_file():
        raise RuntimeError("get-pip.py is missing. Unzip ClassInterpreter-windows-0.3.3.zip with Extract All.")
    log("Installing pip into the bundled Python...")
    code = run(exe, [str(get_pip), "--no-warn-script-location"])
    if code != 0 or not pip_ok(exe):
        raise RuntimeError("pip install failed. Switch to a phone hotspot and double-click OPEN-THIS.bat again.")


def pip_install(exe: str, args: list[str]) -> None:
    trusted = []
    for host in PIP_TRUSTED:
        trusted.extend(["--trusted-host", host])
    last_error = "pip install failed"
    for index in PIP_INDEXES:
        log("pip " + " ".join(args) + "  index=" + index)
        cmd = ["-m", "pip", "--retries", "1", "--timeout", "45", "install", "--index-url", index, *trusted, *args]
        if run(exe, cmd) == 0:
            return
        last_error = "pip failed at " + index
    raise RuntimeError(last_error + ". Switch to a phone hotspot and double-click OPEN-THIS.bat again.")


def status_version(url: str = "http://127.0.0.1:8765/api/status") -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    marker = '"version": "'
    start = body.find(marker)
    if start < 0:
        return None
    start += len(marker)
    end = body.find('"', start)
    if end < 0:
        return None
    return body[start:end]


def configure_env(root: Path) -> None:
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "180")
    os.environ["CLASS_INTERPRET_HF"] = str(root / "hf")
    os.environ["CLASS_INTERPRET_DATA"] = str(root / "data")
    os.environ["PYTHONUTF8"] = "1"
    (root / "hf").mkdir(parents=True, exist_ok=True)
    (root / "data").mkdir(parents=True, exist_ok=True)


def app_version(root: Path) -> str:
    path = root / "VERSION"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip() or VERSION_FALLBACK
    return VERSION_FALLBACK


def main() -> int:
    root = Path(__file__).resolve().parent
    os.chdir(root)
    version = app_version(root)
    log("Class Interpreter " + version)
    log("Folder: " + str(root))
    if is_temp_path(str(root)):
        log("You opened this from INSIDE the zip (Windows Temp).")
        log("This is not a broken laptop.")
        log("Right-click ClassInterpreter-windows-0.3.3.zip -> Extract All,")
        log("then double-click OPEN-THIS.bat.")
        return 1

    wanted = choose_python(root)
    if wanted is None:
        log("Bundled Python is missing. Unzip ClassInterpreter-windows-0.3.3.zip with Extract All.")
        return 1

    running = Path(sys.executable).resolve()
    if running != wanted.resolve():
        log("Switching to " + str(wanted))
        return run(str(wanted), [str(Path(__file__).resolve()), *sys.argv[1:]])

    configure_env(root)
    current = status_version()
    if current == version:
        log("Already running. Opening the browser...")
        try:
            import webbrowser

            webbrowser.open("http://127.0.0.1:8765/?v=" + version)
        except Exception:
            pass
        return 0

    if not packages_ok(sys.executable):
        ensure_pip(root, sys.executable)
        log("Installing packages (first run, keep this window open)...")
        pip_install(sys.executable, ["certifi"])
        pip_install(sys.executable, ["-r", "requirements.txt"])
    else:
        log("Using Python: " + sys.executable)

    if (root / "setup_models.py").is_file():
        if run(sys.executable, ["setup_models.py"]) != 0:
            log("Translation model not installed yet. Use the yellow button after the page opens.")

    log("Starting. Keep this window open. Browser should open at http://127.0.0.1:8765/")
    return run(sys.executable, ["server.py"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        log(str(exc))
        raise SystemExit(1)
