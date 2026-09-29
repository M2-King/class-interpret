"""Local-only classroom interpreter. No account, paid API, or audio upload."""

from __future__ import annotations

import io
import gc
import json
import os
import re
import sys
import threading
import uuid
import webbrowser
from collections import Counter
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, request
from urllib.parse import unquote, urlsplit

import ssl_certs
import whisper_hub

ssl_certs.apply()
whisper_hub.configure()

ROOT = Path(__file__).resolve().parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").is_file() else "0.2.9"
DATA = Path(os.environ.get("CLASS_INTERPRET_DATA", ROOT / "data"))
DATA.mkdir(parents=True, exist_ok=True)
HOST = "127.0.0.1"
PORT = int(os.environ.get("CLASS_INTERPRET_PORT", "8765"))
OLLAMA = "http://127.0.0.1:11434"
MODEL_NAMES = {"small", "medium", "large-v3"}
SESSION_ID = re.compile(r"^[a-f0-9]{32}$")
LOCK = threading.RLock()
MODEL_LOCK = threading.Lock()
TRANSLATE_LOCK = threading.Lock()
TRANSLATE_INSTALL_LOCK = threading.Lock()
WHISPER_INSTALL_LOCK = threading.Lock()
MODEL_CACHE: dict[str, object] = {}
MODEL_DEVICE: dict[str, str] = {}
CUDA_DLL_HANDLES: list[object] = []


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def session_path(session_id: str) -> Path:
    if not SESSION_ID.fullmatch(session_id):
        raise ValueError("无效的课堂编号")
    return DATA / f"{session_id}.json"


def read_session(session_id: str) -> dict:
    path = session_path(session_id)
    if not path.is_file():
        raise FileNotFoundError("没有找到这节课")
    return json.loads(path.read_text(encoding="utf-8"))


def save_session(session: dict) -> None:
    path = session_path(session["id"])
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def install_translation_model() -> None:
    import setup_models

    try:
        setup_models.main()
    except SystemExit as exc:
        if exc.code not in (0, None):
            raise RuntimeError(str(exc) or "翻译模型安装失败") from exc


def translation_available() -> bool:
    try:
        import argostranslate.translate

        languages = {item.code: item for item in argostranslate.translate.get_installed_languages()}
        return "en" in languages and "zh" in languages and bool(
            languages["en"].get_translation(languages["zh"])
        )
    except Exception:
        return False


def translate(text: str) -> str:
    with TRANSLATE_LOCK:
        import argostranslate.translate

        languages = {item.code: item for item in argostranslate.translate.get_installed_languages()}
        if "en" not in languages or "zh" not in languages:
            raise RuntimeError("英语 → 中文翻译模型未安装")
        translator = languages["en"].get_translation(languages["zh"])
        if not translator:
            raise RuntimeError("英语 → 中文翻译模型未安装")
        return translator.translate(text).strip()


def ollama_available() -> bool:
    try:
        with request.urlopen(f"{OLLAMA}/api/tags", timeout=1) as response:
            models = json.load(response).get("models", [])
        return any(item.get("name", "").startswith("deepseek-r1:") for item in models)
    except (OSError, ValueError):
        return False


def load_model(name: str):
    if name not in MODEL_NAMES:
        raise ValueError("不支持的识别模型")
    with MODEL_LOCK:
        if name not in MODEL_CACHE:
            MODEL_CACHE.clear()
            MODEL_DEVICE.clear()
            gc.collect()
            prepare_cuda_dlls()
            model, device = whisper_hub.create_model(name)
            MODEL_CACHE[name] = model
            MODEL_DEVICE[name] = device
        return MODEL_CACHE[name]


def install_whisper_model(name: str = "small") -> None:
    whisper_hub.download(name)


def prepare_cuda_dlls() -> None:
    """Find optional NVIDIA Windows wheels without changing system-wide PATH."""
    if os.name != "nt":
        return
    base = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    for component in ("cublas", "cudnn", "cuda_nvrtc"):
        folder = base / component / "bin"
        if folder.is_dir() and str(folder) not in os.environ.get("PATH", ""):
            os.environ["PATH"] = str(folder) + os.pathsep + os.environ.get("PATH", "")
            CUDA_DLL_HANDLES.append(os.add_dll_directory(str(folder)))


def transcribe(audio: bytes, model_name: str, glossary: str) -> str:
    model = load_model(model_name)
    # Model inference is serialized to avoid exhausting laptop RAM or VRAM.
    with MODEL_LOCK:
        def run(selected_model) -> str:
            segments, _ = selected_model.transcribe(
                io.BytesIO(audio),
                language="en",
                beam_size=5,
                best_of=5,
                condition_on_previous_text=False,
                initial_prompt=("Classroom terminology: " + glossary[:500]) if glossary else None,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 450},
            )
            return " ".join(segment.text.strip() for segment in segments).strip()

        try:
            return run(model)
        except RuntimeError as exc:
            # CTranslate2 can load a CUDA model but fail only when inference starts.
            if not any(term in str(exc).lower() for term in ("cublas", "cudnn", "cuda")):
                raise
            from faster_whisper import WhisperModel

            print("GPU 推理库不可用，自动改用 CPU。")
            cpu_model, device = whisper_hub.create_model(model_name)
            MODEL_CACHE[model_name] = cpu_model
            MODEL_DEVICE[model_name] = device
            return run(cpu_model)


def remove_overlap(previous: str, current: str) -> str:
    """Remove words repeated by the short audio overlap between two chunks."""
    prior = previous.split()
    words = current.split()
    normalize = lambda value: re.sub(r"[^\w]", "", value).casefold()
    for count in range(min(8, len(prior), len(words)), 0, -1):
        if count == 1 and len(normalize(words[0])) < 6:
            continue
        if [normalize(x) for x in prior[-count:]] == [normalize(x) for x in words[:count]]:
            return " ".join(words[count:]).strip()
    return current


def fallback_summary(entries: list[dict], title: str) -> str:
    """An honest transcript digest when a local DeepSeek model is unavailable."""
    usable = [entry for entry in entries if (entry.get("en") or entry.get("zh"))]
    if not usable:
        return "还没有可总结的课堂内容。"
    stopwords = {"about", "after", "again", "also", "because", "before", "could", "from", "have", "just", "like", "more", "next", "some", "that", "them", "there", "these", "this", "today", "very", "what", "when", "where", "which", "will", "with", "would", "your"}
    words = lambda entry: [word for word in re.findall(r"[a-zA-Z]{4,}", entry.get("en", "").lower()) if word not in stopwords]
    frequencies = Counter(word for entry in usable for word in words(entry))
    def score(entry: dict) -> float:
        unique = set(words(entry))
        return sum(min(frequencies[word], 5) for word in unique) / max(1, len(unique) ** 0.5)
    groups: dict[int, list[tuple[int, dict]]] = {}
    for index, entry in enumerate(usable):
        groups.setdefault(index * min(12, len(usable)) // len(usable), []).append((index, entry))
    chosen = sorted((max(group, key=lambda pair: score(pair[1])) for group in groups.values()), key=lambda pair: pair[0])
    selected = [(entry.get("zh") or entry.get("en", "")).strip() for _, entry in chosen]
    task_words = ("作业", "提交", "截止", "考试", "测试", "assignment", "submit", "deadline", "exam")
    tasks = [(entry.get("zh") or entry.get("en", "")).strip() for entry in usable if any(word in (entry.get("zh", "") + " " + entry.get("en", "")).lower() for word in task_words)][:8]
    result = [f"# {title} · 课后速览", "", "以下摘录自课堂记录；未经 DeepSeek 归纳，请核对英文原文。", "", "## 课堂内容摘录"]
    result.extend(f"- {line}" for line in selected)
    if tasks:
        result += ["", "## 可能涉及的任务与考试", *[f"- {line}" for line in tasks]]
    return "\n".join(result)


def ask_deepseek(prompt: str, model: str) -> str:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.2},
    }, ensure_ascii=False).encode("utf-8")
    req = request.Request(f"{OLLAMA}/api/chat", data=payload, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=240) as response:
        result = json.load(response)
    content = result.get("message", {}).get("content", "").strip()
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if not content:
        raise RuntimeError("DeepSeek 没有返回总结")
    return content


def installed_deepseek() -> str | None:
    try:
        with request.urlopen(f"{OLLAMA}/api/tags", timeout=2) as response:
            models = json.load(response).get("models", [])
        names = [item.get("name", "") for item in models]
        for wanted in ("deepseek-r1:8b", "deepseek-r1:7b", "deepseek-r1:1.5b"):
            if wanted in names:
                return wanted
        return next((name for name in names if name.startswith("deepseek-r1:")), None)
    except (OSError, ValueError):
        return None


def make_summary(session: dict) -> tuple[str, str]:
    entries = session.get("entries", [])
    if not entries:
        raise ValueError("这节课还没有内容，暂时无法总结")
    model = installed_deepseek()
    if not model:
        return fallback_summary(entries, session["title"]), "课堂摘录"
    transcript = "\n".join(
        f"[{int(entry.get('at', 0) // 60):02d}:{int(entry.get('at', 0) % 60):02d}] "
        f"EN: {entry.get('en', '')}\nZH: {entry.get('zh', '')}"
        for entry in entries
    )
    blocks = [transcript[i:i + 11000] for i in range(0, len(transcript), 11000)]
    base = "你是留学生的课堂笔记助手。只根据提供的记录写中文总结，不猜测缺失内容。注明不确定或听写可能有误的地方。保留重要英文术语。输出：核心要点、概念与例子、作业/截止时间/考试、待核对问题。没有的信息写“课堂记录中未提及”。"
    try:
        if len(blocks) == 1:
            return ask_deepseek(base + "\n\n课堂记录：\n" + blocks[0], model), f"DeepSeek ({model})"
        parts = [ask_deepseek(base + f"\n\n第 {i + 1}/{len(blocks)} 段课堂记录：\n" + block, model) for i, block in enumerate(blocks)]
        combined = "\n\n".join(parts)
        return ask_deepseek(base + "\n\n请合并以下分段笔记，去重并保留具体任务：\n" + combined[:20000], model), f"DeepSeek ({model})"
    except (OSError, ValueError, RuntimeError):
        return fallback_summary(entries, session["title"]), "课堂摘录（DeepSeek 暂不可用）"


class Handler(BaseHTTPRequestHandler):
    server_version = "ClassInterpret/0.2.9"

    def log_message(self, format: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), format % args))

    def respond(self, status: int, value: object) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def read_body(self, limit: int = 6_000_000) -> bytes:
        size = int(self.headers.get("Content-Length", "0"))
        if size <= 0 or size > limit:
            raise ValueError("请求内容为空或过大")
        return self.rfile.read(size)

    def read_json(self) -> dict:
        data = json.loads(self.read_body().decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("请求格式不正确")
        return data

    def route(self, method: str) -> None:
        path = urlsplit(self.path).path
        pieces = [part for part in path.split("/") if part]
        if method == "GET" and path == "/":
            return self.serve_file("index.html", "text/html; charset=utf-8")
        if method == "GET" and path in ("/app.js", "/style.css"):
            return self.serve_file(path[1:], "text/javascript; charset=utf-8" if path.endswith("js") else "text/css; charset=utf-8")
        if method == "GET" and path == "/api/status":
            models = whisper_hub.cached_models()
            return self.respond(200, {
                "translation": translation_available(),
                "deepseek": installed_deepseek(),
                "version": VERSION,
                "whisper_models": models,
                "whisper": any(models.values()),
            })
        if method == "POST" and path == "/api/translation/install":
            if translation_available():
                return self.respond(200, {"translation": True, "message": "英语 → 中文模型已经安装。"})
            if not TRANSLATE_INSTALL_LOCK.acquire(blocking=False):
                return self.respond(202, {"translation": False, "message": "正在下载翻译模型，请稍候。"})
            try:
                install_translation_model()
            except Exception as exc:
                return self.respond(500, {"error": str(exc), "translation": False})
            finally:
                TRANSLATE_INSTALL_LOCK.release()
            if not translation_available():
                return self.respond(500, {"error": "翻译模型没有装上，请检查网络后重试。", "translation": False})
            return self.respond(200, {"translation": True, "message": "英语 → 中文模型已安装。"})
        if method == "POST" and path == "/api/whisper/install":
            body = {}
            if int(self.headers.get("Content-Length", "0") or 0) > 0:
                try:
                    body = self.read_json()
                except Exception:
                    body = {}
            name = str(body.get("model") or "small")
            if name not in MODEL_NAMES:
                raise ValueError("不支持的识别模型")
            if whisper_hub.cached(name):
                return self.respond(200, {"whisper": True, "model": name, "message": f"语音模型 {name} 已在本地。"})
            if not WHISPER_INSTALL_LOCK.acquire(blocking=False):
                return self.respond(202, {"whisper": False, "message": "正在下载语音模型，请稍候。"})
            try:
                install_whisper_model(name)
            except Exception as exc:
                return self.respond(500, {"error": whisper_hub.friendly_error(exc), "whisper": False})
            finally:
                WHISPER_INSTALL_LOCK.release()
            if not whisper_hub.cached(name):
                return self.respond(500, {"error": "语音模型没有装上。请换手机热点后重试。", "whisper": False})
            return self.respond(200, {"whisper": True, "model": name, "message": f"语音模型 {name} 已下载。"})
        if method == "POST" and path == "/api/shutdown":
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return self.respond(200, {"ok": True})
        if method == "GET" and path == "/api/sessions":
            sessions = []
            for file in DATA.glob("*.json"):
                try:
                    item = json.loads(file.read_text(encoding="utf-8"))
                    sessions.append({"id": item["id"], "title": item["title"], "created": item["created"], "count": len(item["entries"])})
                except (OSError, KeyError, ValueError):
                    pass
            return self.respond(200, sorted(sessions, key=lambda x: x["created"], reverse=True))
        if method == "POST" and path == "/api/sessions":
            body = self.read_json()
            session = {"id": uuid.uuid4().hex, "title": str(body.get("title") or "未命名课堂")[:80], "created": now_iso(), "entries": [], "summary": "", "summary_source": ""}
            with LOCK:
                save_session(session)
            return self.respond(201, session)
        if len(pieces) >= 3 and pieces[:2] == ["api", "sessions"]:
            session_id = pieces[2]
            with LOCK:
                session = read_session(session_id)
            if method == "GET" and len(pieces) == 3:
                return self.respond(200, session)
            if method == "POST" and pieces[3:] == ["chunks"]:
                model = self.headers.get("X-Model", "small")
                if model not in MODEL_NAMES:
                    raise ValueError("不支持的识别模型")
                glossary = unquote(self.headers.get("X-Glossary", ""))[:500]
                elapsed = float(self.headers.get("X-Elapsed", "0"))
                audio = self.read_body()
                if audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
                    raise ValueError("需要 16 kHz 的 WAV 录音")
                try:
                    english = transcribe(audio, model, glossary)
                except Exception as exc:
                    raise RuntimeError(whisper_hub.friendly_error(exc)) from exc
                with LOCK:
                    session = read_session(session_id)
                    if session["entries"] and english:
                        english = remove_overlap(session["entries"][-1]["en"], english)
                if not english:
                    return self.respond(200, {"entry": None})
                try:
                    chinese = translate(english)
                    translation_error = ""
                except Exception as exc:
                    chinese = ""
                    translation_error = str(exc)
                entry = {"id": uuid.uuid4().hex, "at": max(0, elapsed), "en": english, "zh": chinese}
                with LOCK:
                    session = read_session(session_id)
                    session["entries"].append(entry)
                    session["summary"] = ""
                    save_session(session)
                return self.respond(200, {"entry": entry, "translation_error": translation_error, "device": MODEL_DEVICE.get(model, "")})
            if method == "PATCH" and len(pieces) == 5 and pieces[3] == "entries":
                body = self.read_json()
                with LOCK:
                    session = read_session(session_id)
                    entry = next((item for item in session["entries"] if item["id"] == pieces[4]), None)
                    if entry is None:
                        raise FileNotFoundError("没有找到这一条课堂记录")
                    entry["en"] = str(body.get("en", entry["en"]))[:5000]
                    entry["zh"] = str(body.get("zh", entry["zh"]))[:5000]
                    session["summary"] = ""
                    save_session(session)
                return self.respond(200, entry)
            if method == "POST" and pieces[3:] == ["summary"]:
                summary, source = make_summary(session)
                with LOCK:
                    session = read_session(session_id)
                    session["summary"] = summary
                    session["summary_source"] = source
                    save_session(session)
                return self.respond(200, {"summary": summary, "source": source})
        return self.respond(404, {"error": "未找到"})

    def serve_file(self, name: str, content_type: str) -> None:
        payload = (ROOT / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        self.safe_route("GET")

    def do_POST(self) -> None:
        self.safe_route("POST")

    def do_PATCH(self) -> None:
        self.safe_route("PATCH")

    def safe_route(self, method: str) -> None:
        try:
            self.route(method)
        except FileNotFoundError as exc:
            self.respond(404, {"error": str(exc)})
        except (ValueError, json.JSONDecodeError) as exc:
            self.respond(400, {"error": str(exc)})
        except Exception as exc:
            print(f"处理失败: {exc!r}")
            self.respond(500, {"error": str(exc)})


def main() -> None:
    address = f"http://{HOST}:{PORT}/"
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"课堂同传已启动：{address}")

    def warmup() -> None:
        try:
            whisper_hub.download("small")
        except Exception as exc:
            print(f"后台下载语音模型失败：{whisper_hub.friendly_error(exc)}")

    threading.Thread(target=warmup, daemon=True).start()
    if os.environ.get("CLASS_INTERPRET_NO_BROWSER") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(address)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("已退出。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
