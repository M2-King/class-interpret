"""Quality-controlled English-to-Chinese live translation."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

try:
    import deepseek_api
except ModuleNotFoundError:
    class _UnavailableDeepSeekAPI:
        @staticmethod
        def available(*_args, **_kwargs) -> bool:
            return False

        @staticmethod
        def chat(*_args, **_kwargs) -> str:
            raise RuntimeError("DeepSeek cloud translation is unavailable.")

    deepseek_api = _UnavailableDeepSeekAPI()

_RTF_CONTROL = re.compile(
    r"(?:\{\\|\\(?:fn|fs|fcharset|bord|shad|[34]c|alpha|pos|an)\w*\b)",
    re.IGNORECASE,
)
_HTML = re.compile(r"<\s*/?\s*(?:script|style|iframe|object|html|body|div|span)\b", re.IGNORECASE)
_THINK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_CJK = re.compile(r"[\u3400-\u9fff]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_LEADING_LABEL = re.compile(r"^(?:翻译|译文|中文|translation)\s*[:：]\s*", re.IGNORECASE)


class TranslationRejected(RuntimeError):
    """Raised when a provider returned unsafe or obviously contaminated text."""


def clean_plain_text(value: str) -> str:
    text = _THINK.sub("", str(value or "")).strip()
    text = text.removeprefix("```text").removeprefix("```markdown").removeprefix("```")
    text = text.removesuffix("```").strip()
    text = _LEADING_LABEL.sub("", text).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'", "“", "”"}:
        text = text[1:-1].strip()
    return text


def validate_translation(source: str, value: str) -> str:
    text = clean_plain_text(value)
    if not text:
        raise TranslationRejected("翻译结果为空")
    if _RTF_CONTROL.search(text) or _HTML.search(text) or _CONTROL.search(text):
        raise TranslationRejected("翻译结果包含异常格式代码")
    if len(text) > max(1200, len(source) * 8):
        raise TranslationRejected("翻译结果异常过长")
    if source.strip() and not _CJK.search(text):
        raise TranslationRejected("翻译结果没有中文")
    compact = re.sub(r"\s+", "", text)
    if len(compact) >= 24:
        for size in range(4, min(16, len(compact) // 3 + 1)):
            token = compact[:size]
            if token and compact.count(token) >= 4:
                raise TranslationRejected("翻译结果包含异常重复")
    return text


def offline_preview(source: str, translate: Callable[[str], str]) -> str:
    return validate_translation(source, translate(source))


def cloud_translation(
    source: str,
    *,
    glossary: str = "",
    context: Iterable[str] = (),
    timeout: int = 18,
) -> str:
    previous = "\n".join(item.strip() for item in context if item and item.strip())[-1600:]
    terms = glossary.strip()[:800]
    prompt = (
        "你是实时课堂字幕翻译器。把 CURRENT 中的英文准确翻译成简体中文。\n"
        "只返回一段纯文本中文译文，不要解释，不要 Markdown，不要 RTF/HTML 格式代码。\n"
        "保持公式、代码、缩写、数字和专有名词；结合上下文修正断句，但不要添加原文没有的信息。\n"
        f"COURSE TERMS:\n{terms or '(none)'}\n"
        f"PREVIOUS CONTEXT:\n{previous or '(none)'}\n"
        f"CURRENT:\n{source.strip()}"
    )
    return validate_translation(source, deepseek_api.chat(prompt, timeout=timeout))


def best_translation(
    source: str,
    offline: Callable[[str], str],
    *,
    glossary: str = "",
    context: Iterable[str] = (),
    prefer_cloud: bool = True,
) -> tuple[str, str, str]:
    """Return text, provider, quality with a safe offline fallback."""
    cloud_error: BaseException | None = None
    if prefer_cloud and deepseek_api.available():
        try:
            return cloud_translation(source, glossary=glossary, context=context), "deepseek", "final"
        except Exception as exc:
            cloud_error = exc
    try:
        return offline_preview(source, offline), "argos", "provisional" if cloud_error else "offline"
    except Exception as offline_error:
        if cloud_error:
            raise RuntimeError(f"在线翻译失败：{cloud_error}；离线翻译失败：{offline_error}") from offline_error
        raise
