"""Download faster-whisper models with a Hugging Face China mirror fallback."""

from __future__ import annotations

import os
from pathlib import Path

REPOS = {
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
}
MODEL_SIZE_ESTIMATES = {
    "small": 488_000_000,
    "medium": 1_530_000_000,
    "large-v3": 3_100_000_000,
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


def bundled_model_dir(name: str) -> Path | None:
    """Return a complete, directly loadable local model folder when available.

    Release installers put the ready-to-use Small model in ``hf/bundled``.
    Older Windows packages downloaded the same CTranslate2 files through
    ModelScope, so keep recognizing that layout as well.
    """
    if name not in REPOS:
        return None
    hf_home = Path(os.environ.get("CLASS_INTERPRET_HF") or configure()).expanduser()
    candidates = (
        hf_home / "bundled" / f"faster-whisper-{name}",
        hf_home / "modelscope" / f"gpustack--faster-whisper-{name}",
    )
    for folder in candidates:
        if (folder / "model.bin").is_file() and (folder / "config.json").is_file():
            return folder
    return None


def cached(name: str) -> bool:
    if name not in REPOS:
        return False
    if bundled_model_dir(name) is not None:
        return True
    folder = cache_dir(name)
    if not folder.is_dir():
        return False
    return any(folder.rglob("model.bin")) or any(folder.rglob("*.bin"))


def cached_models() -> dict[str, bool]:
    configure()
    return {name: cached(name) for name in REPOS}


def cached_bytes(name: str) -> int:
    """Return downloaded bytes, including partial Hugging Face cache files."""
    if name not in REPOS:
        return 0
    folders = [cache_dir(name)]
    bundled = bundled_model_dir(name)
    if bundled is not None:
        folders.append(bundled)
    total = 0
    seen: set[Path] = set()
    for folder in folders:
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            try:
                total += path.stat().st_size
            except OSError:
                pass
    return total


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


def instantiate(name: str, *, local_files_only: bool, force_cpu: bool = False):
    """Load faster-whisper the same way this morning's server.py did: CUDA, then CPU.

    faster-whisper/CTranslate2 only understands NVIDIA CUDA or CPU. A Mac GPU is
    Metal (Apple Silicon) or Intel graphics, so the CUDA attempt fails there and
    we use CPU — same as the old backend. force_cpu is for the inference fallback
    when CUDA loaded but cublas/cudnn then failed.
    """
    from faster_whisper import WhisperModel

    local_folder = bundled_model_dir(name) if local_files_only else None
    model_source = str(local_folder) if local_folder is not None else name
    # A path is already local and must not receive Hugging Face-only options.
    kwargs = {"local_files_only": True} if local_files_only and local_folder is None else {}
    if force_cpu:
        return WhisperModel(model_source, device="cpu", compute_type="int8", **kwargs), "CPU"
    try:
        return WhisperModel(model_source, device="cuda", compute_type="int8_float16", **kwargs), "GPU"
    except Exception:
        return WhisperModel(model_source, device="cpu", compute_type="int8", **kwargs), "CPU"


def create_model(name: str, *, force_cpu: bool = False):
    configure()
    last_error: BaseException | None = None
    if cached(name):
        try:
            return instantiate(name, local_files_only=True, force_cpu=force_cpu)
        except Exception as exc:
            last_error = exc
    for url in endpoints():
        os.environ["HF_ENDPOINT"] = url
        print(f"正在从 {url} 获取语音模型 {name}……")
        try:
            return instantiate(name, local_files_only=False, force_cpu=force_cpu)
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
