"""DeepSeek cloud chat using an encrypted API key file. No key is logged."""

from __future__ import annotations

import json
import os
import re
import ssl
from pathlib import Path
from urllib import error, request

import secret_box

CLOUD_URL = os.environ.get("CLASS_INTERPRET_DEEPSEEK_URL", "https://api.deepseek.com/chat/completions")
CLOUD_MODEL = os.environ.get("CLASS_INTERPRET_DEEPSEEK_MODEL", "deepseek-chat")
PLAIN_NAME = "deepseek.api"
ENC_NAME = "deepseek_api.enc"


def support_root() -> Path:
    data = os.environ.get("CLASS_INTERPRET_DATA")
    if data:
        return Path(data).expanduser().resolve().parent
    return Path(__file__).resolve().parent


def parse_plaintext(text: str) -> str | None:
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("bearer "):
            line = line[7:].strip()
        return line or None
    return None


def _plain_paths(root: Path) -> list[Path]:
    return [root / "secrets" / PLAIN_NAME, root / PLAIN_NAME]


def _enc_paths(root: Path) -> list[Path]:
    return [root / ENC_NAME, root / "secrets" / ENC_NAME]


def seal_from_plaintext(plain: Path, dest: Path) -> Path:
    key = parse_plaintext(plain.read_text(encoding="utf-8"))
    if not key:
        raise ValueError("secrets/deepseek.api 还是空的，请把 DeepSeek API key 贴进去")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(secret_box.seal(key))
    return dest


def _ssl_context():
    try:
        import ssl_certs

        bundle = ssl_certs.apply()
        if bundle:
            return ssl.create_default_context(cafile=str(bundle))
    except Exception:
        pass
    return ssl.create_default_context()


def load_key(root: Path | None = None) -> str | None:
    env = (os.environ.get("CLASS_INTERPRET_DEEPSEEK_API") or "").strip()
    if env:
        return env
    base = root or support_root()
    for path in _plain_paths(base):
        if not path.is_file():
            continue
        key = parse_plaintext(path.read_text(encoding="utf-8"))
        if not key:
            continue
        enc = _enc_paths(base)[0]
        try:
            if not enc.is_file() or secret_box.unseal(enc.read_bytes()) != key:
                seal_from_plaintext(path, enc)
        except Exception:
            seal_from_plaintext(path, enc)
        return key
    for path in _enc_paths(base):
        if not path.is_file():
            continue
        try:
            return secret_box.unseal(path.read_bytes())
        except Exception:
            continue
    return None


def available(root: Path | None = None) -> bool:
    return bool(load_key(root))


def friendly_error(exc: BaseException) -> str:
    text = str(exc)
    lowered = text.lower()
    if any(token in text or token in lowered for token in (
        "timed out", "timeout", "ssl", "certificate", "Errno 60", "api.deepseek",
        "401", "403", "402", "insufficient", "authentication",
    )):
        return (
            "DeepSeek 云接口暂时不可用。请换手机热点后重试。"
            "若一直失败，检查 secrets/deepseek.api 里的 key 是否有效。"
        )
    return text


def chat(prompt: str, *, key: str | None = None, timeout: int = 120) -> str:
    token = key if key is not None else load_key()
    if not token:
        raise RuntimeError("还没有 DeepSeek API key")
    payload = json.dumps({
        "model": CLOUD_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        CLOUD_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout, context=_ssl_context()) as response:
            result = json.load(response)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(friendly_error(RuntimeError(f"{exc.code} {detail}"))) from exc
    except Exception as exc:
        raise RuntimeError(friendly_error(exc)) from exc
    choices = result.get("choices") or []
    message = (choices[0].get("message") if choices else {}) or {}
    content = str(message.get("content") or "").strip()
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if not content:
        content = str(message.get("reasoning_content") or "").strip()
    if not content:
        raise RuntimeError("DeepSeek 没有返回总结")
    return content
