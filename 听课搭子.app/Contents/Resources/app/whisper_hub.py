"""Download faster-whisper models with a Hugging Face China mirror fallback."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPOS = {
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
}
MIRRORS = ("https://hf-mirror.com", "https://huggingface.co")


def support_root() -> Path:
    data = os.environ.get("CLASS_INTERPRET_DATA")
    if data:
        return Path(data).expanduser().resolve().parent
    return Path(__file__).resolve().parent


def configure() -> Path:
    root = support_root()
    hf_home = Path(os.environ.get("CLASS_INTERPRET_HF", root / "hf")).expanduser()
    hf_home.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(hf_home)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hf_home / "hub")
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "180")
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "30")
    if not os.environ.get("CLASS_INTERPRET_HF_OFFICIAL"):
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    return hf_home


def cache_dir(name: str) -> Path:
    repo = REPOS[name]
    hub = Path(os.environ.get("HUGGINGFACE_HUB_CACHE") or (configure() / "hub"))
    return hub / f"models--{repo.replace('/', '--')}"


def cached(name: str) -> bool:
    if name not in REPOS:
        return False
    folder = cache_dir(name)
    if not folder.is_dir():
        return False
    return any(folder.rglob("model.bin")) or any(folder.rglob("*.bin"))


def cached_models() -> dict[str, bool]:
    configure()
    return {name: cached(name) for name in REPOS}


def endpoints() -> list[str]:
    ordered: list[str] = []
    for item in (os.environ.get("HF_ENDPOINT"), *MIRRORS):
        if item and item not in ordered:
            ordered.append(item)
    return ordered


def friendly_error(exc: BaseException) -> str:
    text = str(exc)
    lowered = text.lower()
    if any(token in text or token in lowered for token in (
        "ConnectTimeout", "timed out", "Hub", "huggingface", "Errno 60", "snapshot folder",
    )):
        return (
            "语音识别模型还没下载完。校园网经常连不上 Hugging Face。"
            "请换手机热点，点黄色条「下载语音模型」，建议先用 Small。"
        )
    return text


def create_model(name: str):
    from faster_whisper import WhisperModel

    configure()
    last_error: BaseException | None = None
    use_cuda = sys.platform.startswith("linux") or os.name == "nt"
    if cached(name):
        try:
            return WhisperModel(name, device="cpu", compute_type="int8", local_files_only=True), "CPU"
        except Exception as exc:
            last_error = exc
    for url in endpoints():
        os.environ["HF_ENDPOINT"] = url
        print(f"正在从 {url} 获取语音模型 {name}……")
        try:
            if use_cuda:
                try:
                    return WhisperModel(name, device="cuda", compute_type="int8_float16"), "GPU"
                except Exception:
                    pass
            return WhisperModel(name, device="cpu", compute_type="int8"), "CPU"
        except Exception as exc:
            last_error = exc
            print(f"{url} 下载失败：{exc}")
    raise RuntimeError(friendly_error(last_error or RuntimeError("语音模型下载失败")))


def download(name: str = "small") -> None:
    if name not in REPOS:
        raise ValueError("不支持的识别模型")
    if cached(name):
        print(f"语音模型 {name} 已在本地。")
        return
    create_model(name)
    if not cached(name):
        raise RuntimeError("语音模型没有保存到本地，请换手机热点后重试。")
    print(f"语音模型 {name} 已下载。")
