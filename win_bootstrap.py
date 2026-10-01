"""Windows first-launch helper. Stdlib only. Prefer an existing .venv, else bundled Python."""

from __future__ import annotations

import os
import subprocess
import sys
import time
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


def find_venv_root(start: Path) -> Path | None:
    current = Path(start).resolve()
    for _ in range(3):
        exe = current / ".venv" / "Scripts" / "python.exe"
        try:
            if exe.is_file() and exe.stat().st_size >= 4096:
                return current
        except OSError:
            pass
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def choose_python(root: Path) -> Path | None:
    venv_root = find_venv_root(root)
    if venv_root is not None:
        return venv_root / ".venv" / "Scripts" / "python.exe"
    bundled = Path(root) / ".runtime" / "python" / "python.exe"
    try:
        if bundled.is_file() and bundled.stat().st_size >= 4096:
            return bundled
    except OSError:
        pass
    return None


def enable_embed_site(exe: str) -> None:
    dest = Path(exe).resolve().parent
    if not dest.is_dir():
        return
    zips = sorted(dest.glob("python*.zip"))
    zip_name = zips[0].name if zips else "python312.zip"
    pths = sorted(dest.glob("python*._pth"))
    pth_path = pths[0] if pths else dest / "python312._pth"
    pth_path.write_bytes(
        (zip_name + "\r\n.\r\nLib\\site-packages\r\nimport site\r\n").encode("ascii")
    )


def log(message: str) -> None:
    print(message, flush=True)


def run(exe: str, args: list[str]) -> int:
    completed = subprocess.run([exe, *args], check=False)
    return int(completed.returncode or 0)


def pip_ok(exe: str) -> bool:
    return run(exe, ["-m", "pip", "--version"]) == 0


def packages_ok(exe: str) -> bool:
    return run(exe, ["-c", "import faster_whisper, argostranslate, websockets"]) == 0


def ensure_pip(root: Path, exe: str) -> None:
    enable_embed_site(exe)
    if pip_ok(exe):
        return
    pyz = Path(root) / "pip.pyz"
    if (not pyz.is_file()) or pyz.stat().st_size < 10000:
        try:
            log("Downloading pip.pyz (Python 3.12 has no distutils)...")
            urllib.request.urlretrieve("https://bootstrap.pypa.io/pip/pip.pyz", pyz)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            log("pip.pyz download failed: " + str(exc))
    if pyz.is_file() and pyz.stat().st_size >= 10000:
        log("Installing pip with pip.pyz...")
        run(exe, [str(pyz), "install", "--no-warn-script-location", "pip"])
        enable_embed_site(exe)
        if pip_ok(exe):
            return
    get_pip = root / "get-pip.py"
    if not get_pip.is_file():
        raise RuntimeError("pip.pyz/get-pip.py missing. Unzip ClassInterpreter-windows-0.3.3.zip with Extract All.")
    log("Installing pip into the bundled Python...")
    run(exe, [str(get_pip), "--no-warn-script-location"])
    enable_embed_site(exe)
    if pip_ok(exe):
        return
    raise RuntimeError("pip install failed. Switch to a phone hotspot and double-click OPEN-THIS.bat again.")


def try_cuda_libs(exe: str) -> None:
    if os.name != "nt":
        return
    log("Trying NVIDIA CUDA libs for this GPU (optional, large download)...")
    try:
        pip_install(exe, ["nvidia-cublas-cu12", "nvidia-cudnn-cu12"])
    except RuntimeError as exc:
        log("CUDA libs skipped (CPU still works): " + str(exc))


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


def stop_listener(port: int = 8765, wait: float = 1) -> None:
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/shutdown",
            data=b"",
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2).read()
    except (urllib.error.URLError, TimeoutError, OSError):
        pass
    if wait:
        time.sleep(wait)


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
    os.environ["PYTHONUTF8"] = "1"
    hf = Path(root) / "hf"
    data = Path(root) / "data"
    venv_root = find_venv_root(root)
    if venv_root is not None:
        parent_hf = venv_root / "hf"
        parent_data = venv_root / "data"
        if parent_hf.is_dir():
            hf = parent_hf
        if parent_data.is_dir():
            data = parent_data
    os.environ["CLASS_INTERPRET_HF"] = str(hf)
    os.environ["CLASS_INTERPRET_DATA"] = str(data)
    hf.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)


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
    venv_root = find_venv_root(root)
    if venv_root is not None and wanted == venv_root / ".venv" / "Scripts" / "python.exe":
        log("Using existing .venv: " + str(wanted))

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
    if current:
        log("Stopping old server " + current + " ...")
        stop_listener()

    if not packages_ok(sys.executable):
        ensure_pip(root, sys.executable)
        log("Installing packages (first run, keep this window open)...")
        pip_install(sys.executable, ["certifi"])
        pip_install(sys.executable, ["-r", "requirements.txt"])
        try_cuda_libs(sys.executable)
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
