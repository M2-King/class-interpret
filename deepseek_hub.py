"""Install and talk to a local DeepSeek-R1 model through Ollama. No paid API."""

from __future__ import annotations

import io
import json
import os
import platform
import re
import shutil
import ssl
import stat
import subprocess
import sys
import tarfile
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from urllib import error, request

PREFERRED_MODELS = ("deepseek-r1:8b", "deepseek-r1:7b", "deepseek-r1:1.5b")
DEFAULT_MODEL = "deepseek-r1:1.5b"
HOST = os.environ.get("CLASS_INTERPRET_OLLAMA", "http://127.0.0.1:11434")
GITHUB_LATEST = "https://github.com/ollama/ollama/releases/latest/download"
ProgressCallback = Callable[[int, str, str, int, int], None]


def _progress(callback: ProgressCallback | None, percent: int, phase: str, detail: str, downloaded: int = 0, total: int = 0) -> None:
    if callback:
        callback(percent, phase, detail, downloaded, total)


def support_root() -> Path:
    data = os.environ.get("CLASS_INTERPRET_DATA")
    if data:
        return Path(data).expanduser().resolve().parent
    return Path(__file__).resolve().parent


def runtime_dir() -> Path:
    override = os.environ.get("CLASS_INTERPRET_OLLAMA_HOME")
    if override:
        path = Path(override).expanduser()
    else:
        path = support_root() / ".runtime" / "ollama"
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_model(name: str | None) -> str:
    value = (name or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if value not in PREFERRED_MODELS:
        raise ValueError("不支持的 DeepSeek 型号，请使用 deepseek-r1:1.5b / 7b / 8b")
    return value


def pick_model(names: list[str]) -> str | None:
    for wanted in PREFERRED_MODELS:
        if wanted in names:
            return wanted
    return next((item for item in names if item.startswith("deepseek-r1:")), None)


def friendly_error(exc: BaseException) -> str:
    text = str(exc)
    lowered = text.lower()
    if any(token in text or token in lowered for token in (
        "timed out", "timeout", "ConnectTimeout", "Errno 60", "Errno 110",
        "ollama", "registry", "connection refused", "Name or service not known",
    )):
        return (
            "本机 DeepSeek 还没装好。需要免费的 Ollama 和 deepseek-r1 模型（建议 1.5b，约 1.1GB）。"
            "校园网经常失败，请换手机热点后点「安装 DeepSeek」。不使用付费 API。"
        )
    return text


def archive_urls(system: str | None = None, machine: str | None = None) -> list[str]:
    system = (system or sys.platform).lower()
    machine = (machine or platform.machine()).lower()
    if system.startswith("darwin"):
        names = ["ollama-darwin.tgz"]
    elif system.startswith("win") or system == "nt":
        names = ["ollama-windows-arm64.zip"] if "arm" in machine else ["ollama-windows-amd64.zip"]
    elif machine in {"aarch64", "arm64"}:
        names = ["ollama-linux-arm64.tgz", "ollama-linux-arm64.tar.gz"]
    else:
        names = ["ollama-linux-amd64.tgz", "ollama-linux-amd64.tar.gz"]
    return [f"{GITHUB_LATEST}/{name}" for name in names]


def _is_ollama_binary(path: Path) -> bool:
    if not path.is_file():
        return False
    name = path.name.lower()
    return name in {"ollama", "ollama.exe"}


def extract_archive(archive: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)
    else:
        with tarfile.open(archive) as tar:
            tar.extractall(dest)
    found = [path for path in dest.rglob("*") if _is_ollama_binary(path)]
    if not found:
        raise RuntimeError("Ollama 压缩包里没有可执行文件")
    binary = next((path for path in found if path.parent == dest), found[0])
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return binary


def find_binary() -> Path | None:
    which = shutil.which("ollama")
    candidates: list[Path] = []
    if which:
        candidates.append(Path(which))
    extra = [
        Path("/usr/local/bin/ollama"),
        Path("/opt/homebrew/bin/ollama"),
        Path("/Applications/Ollama.app/Contents/Resources/ollama"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Ollama" / "ollama.exe",
        runtime_dir() / "ollama.exe",
        runtime_dir() / "ollama",
    ]
    for folder in (runtime_dir(),):
        extra.extend(folder.rglob("ollama.exe"))
        extra.extend(folder.rglob("ollama"))
    candidates.extend(extra)
    seen: set[str] = set()
    for path in candidates:
        try:
            resolved = path.expanduser()
        except OSError:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        if _is_ollama_binary(resolved):
            return resolved
    return None


def reachable(timeout: float = 1.5) -> bool:
    try:
        with request.urlopen(f"{HOST}/api/tags", timeout=timeout) as response:
            json.load(response)
        return True
    except (OSError, ValueError, error.URLError):
        return False


def list_models() -> list[str]:
    with request.urlopen(f"{HOST}/api/tags", timeout=3) as response:
        models = json.load(response).get("models", [])
    names: list[str] = []
    for item in models:
        name = item.get("name") or item.get("model") or ""
        if name:
            names.append(name)
    return names


def installed() -> str | None:
    try:
        return pick_model(list_models())
    except (OSError, ValueError, error.URLError):
        return None


def snapshot() -> dict:
    model = installed()
    binary = find_binary()
    return {
        "ollama": reachable(),
        "deepseek": model,
        "ready": bool(model),
        "binary": str(binary) if binary else "",
        "default_model": DEFAULT_MODEL,
    }


def _ssl_context():
    try:
        import ssl_certs

        bundle = ssl_certs.apply()
        if bundle:
            return ssl.create_default_context(cafile=str(bundle))
    except Exception:
        pass
    return ssl.create_default_context()


def _download(url: str, dest: Path, progress: ProgressCallback | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = request.Request(url, headers={"User-Agent": "class-interpret"})
    with request.urlopen(req, timeout=600, context=_ssl_context()) as response, dest.open("wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        while True:
            block = response.read(1024 * 256)
            if not block:
                break
            out.write(block)
            downloaded += len(block)
            percent = min(20, int(downloaded * 20 / total)) if total else 5
            _progress(progress, percent, "Downloading Ollama", "Downloading the local AI runtime...", downloaded, total)


def _try_winget() -> Path | None:
    if os.name != "nt":
        return None
    winget = shutil.which("winget")
    if not winget:
        return None
    try:
        subprocess.run(
            [winget, "install", "-e", "--id", "Ollama.Ollama", "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity"],
            check=False,
            timeout=600,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return find_binary()


def download_ollama(progress: ProgressCallback | None = None) -> Path:
    existing = find_binary()
    if existing:
        _progress(progress, 20, "Ollama ready", "Using the existing local AI runtime.")
        return existing
    _progress(progress, 3, "Preparing Ollama", "Checking for an existing local AI runtime...")
    winget_binary = _try_winget()
    if winget_binary:
        return winget_binary
    last_error: BaseException | None = None
    dest_dir = runtime_dir()
    for url in archive_urls():
        archive = dest_dir / Path(url).name.split("?")[0]
        print(f"正在下载 Ollama：{url}")
        try:
            _download(url, archive, progress)
            _progress(progress, 22, "Installing Ollama", "Unpacking the local AI runtime...")
            binary = extract_archive(archive, dest_dir)
            return binary
        except Exception as exc:
            last_error = exc
            print(f"Ollama 下载失败：{exc}")
    raise RuntimeError(friendly_error(last_error or RuntimeError("Ollama 下载失败")))


def start_server(binary: Path | None = None) -> None:
    if reachable():
        return
    binary = binary or find_binary()
    if not binary:
        raise RuntimeError("没有找到 Ollama 程序")
    env = os.environ.copy()
    env.setdefault("OLLAMA_HOST", HOST.replace("http://", "").replace("https://", ""))
    if str(runtime_dir()) in str(binary):
        env.setdefault("OLLAMA_MODELS", str(support_root() / "ollama-models"))
    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "env": env,
        "start_new_session": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        kwargs.pop("start_new_session", None)
    subprocess.Popen([str(binary), "serve"], **kwargs)
    deadline = time.time() + 45
    while time.time() < deadline:
        if reachable():
            return
        time.sleep(0.4)
    if not reachable():
        raise RuntimeError("Ollama 已安装但没有启动成功")


def try_start() -> None:
    try:
        if reachable():
            return
        binary = find_binary()
        if not binary:
            return
        start_server(binary)
    except Exception as exc:
        print(f"后台启动 Ollama 失败：{exc}")


def pull(name: str, progress: ProgressCallback | None = None) -> None:
    payload = json.dumps({"name": name, "stream": True}).encode("utf-8")
    req = request.Request(f"{HOST}/api/pull", data=payload, headers={"Content-Type": "application/json"})
    last = ""
    with request.urlopen(req, timeout=900) as response:
        for raw in response:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except ValueError:
                continue
            last = item.get("error") or item.get("status") or last
            if item.get("error"):
                raise RuntimeError(item["error"])
            status = str(item.get("status") or "")
            completed = int(item.get("completed") or 0)
            total = int(item.get("total") or 0)
            percent = 28 + (int(completed * 70 / total) if total else 0)
            _progress(progress, min(98, percent), "Downloading DeepSeek", status or f"Downloading {name}...", completed, total)
            if status.lower() in {"success", "complete"} or "success" in status.lower():
                return
    if last:
        print(f"Ollama pull: {last}")


def install(name: str | None = None, progress: ProgressCallback | None = None) -> str:
    model = normalize_model(name)
    current = installed()
    if current == model or (current and name is None):
        return current or model
    binary = download_ollama(progress)
    _progress(progress, 25, "Starting Ollama", "Starting the local model service...")
    start_server(binary)
    print(f"正在拉取 DeepSeek 模型 {model}……")
    try:
        pull(model, progress)
    except Exception as exc:
        raise RuntimeError(friendly_error(exc)) from exc
    ready = installed()
    if not ready:
        raise RuntimeError("DeepSeek 模型没有装上。请换手机热点后重试。")
    _progress(progress, 100, "DeepSeek ready", f"Installed {ready}.")
    return ready


def chat(prompt: str, model: str, timeout: int = 240) -> str:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.2},
    }, ensure_ascii=False).encode("utf-8")
    req = request.Request(f"{HOST}/api/chat", data=payload, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=timeout) as response:
        result = json.load(response)
    content = result.get("message", {}).get("content", "").strip()
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if not content:
        raise RuntimeError("DeepSeek 没有返回总结")
    return content
