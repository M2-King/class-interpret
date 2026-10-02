"""Loopback-only WebSocket transport for low-latency classroom captions."""

from __future__ import annotations

import json
import secrets
import threading
import time
from collections.abc import Callable
from typing import Any

from streaming_hub import DecodeJob, LiveBuffer


class StreamingServer:
    """Small companion server that never listens beyond localhost."""

    def __init__(
        self,
        host: str,
        port: int,
        decode: Callable[[DecodeJob, dict], str],
        save_final: Callable[[DecodeJob, str, dict], dict | None],
        translate_final: Callable[[dict, dict], object],
        translate_partial: Callable[[str, dict], str] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.decode = decode
        self.save_final = save_final
        self.translate_final = translate_final
        self.translate_partial = translate_partial
        self.token = secrets.token_urlsafe(24)
        self._server: Any = None
        self._thread: threading.Thread | None = None
        self.error = ""

    @property
    def ready(self) -> bool:
        return self._server is not None and not self.error

    def config(self) -> dict:
        return {
            "enabled": self.ready,
            "url": f"ws://{self.host}:{self.port}",
            "token": self.token if self.ready else "",
            "sample_rate": 16000,
            "error": self.error,
        }

    def start(self) -> None:
        try:
            from websockets.sync.server import serve

            self._server = serve(
                self._handle,
                self.host,
                self.port,
                max_size=256_000,
                compression=None,
                open_timeout=5,
                close_timeout=3,
            )
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                name="class-interpreter-stream",
                daemon=True,
            )
            self._thread.start()
        except Exception as exc:
            self.error = str(exc)
            self._server = None
            print(f"实时字幕服务未启动，将使用兼容模式：{exc}")

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._server = None

    @staticmethod
    def _settings(message: dict) -> dict:
        return {
            "session_id": str(message.get("session_id") or ""),
            "model": str(message.get("model") or "small"),
            "glossary": str(message.get("glossary") or "")[:500],
            "base_elapsed": max(0.0, float(message.get("base_elapsed") or 0)),
        }

    def _handle(self, connection) -> None:
        send_lock = threading.Lock()
        buffer = LiveBuffer()
        settings: dict = {}
        stopped = threading.Event()
        work_ready = threading.Event()
        worker_done = threading.Event()
        partial_lock = threading.Lock()
        partial_pending: dict | None = None
        partial_worker_running = False

        def send(payload: dict) -> None:
            try:
                with send_lock:
                    connection.send(json.dumps(payload, ensure_ascii=False))
            except Exception:
                stopped.set()

        def translate(entry: dict) -> None:
            try:
                updates = self.translate_final(entry, settings)
                if isinstance(updates, dict):
                    updates = (updates,)
                for translated in updates or ():
                    if translated:
                        send({"type": "translation", "entry": translated})
            except Exception as exc:
                send({"type": "translation_error", "entry_id": entry.get("id"), "message": str(exc)})

        def queue_partial_translation(event: dict) -> None:
            nonlocal partial_pending, partial_worker_running
            if self.translate_partial is None:
                return
            with partial_lock:
                partial_pending = dict(event)
                if partial_worker_running:
                    return
                partial_worker_running = True

            def run() -> None:
                nonlocal partial_pending, partial_worker_running
                while not stopped.is_set():
                    with partial_lock:
                        current = partial_pending
                        partial_pending = None
                    if current is None:
                        with partial_lock:
                            if partial_pending is None:
                                partial_worker_running = False
                                return
                        continue
                    try:
                        chinese = self.translate_partial(current["text"], settings)
                    except Exception:
                        chinese = ""
                    with partial_lock:
                        stale = partial_pending is not None
                    if chinese and not stale and not stopped.is_set():
                        send({
                            "type": "partial_translation",
                            "utterance_id": current.get("utterance_id"),
                            "text": current["text"],
                            "zh": chinese,
                            "translation_status": "provisional",
                        })

            threading.Thread(target=run, name="partial-translator", daemon=True).start()

        def worker() -> None:
            try:
                while True:
                    job = buffer.next_job(settings.get("elapsed", 0.0))
                    if job is None:
                        if stopped.is_set() and not buffer.pending():
                            break
                        work_ready.wait(0.08)
                        work_ready.clear()
                        continue
                    try:
                        text = self.decode(job, settings)
                    except Exception as exc:
                        send({"type": "error", "message": str(exc), "recoverable": True})
                        continue
                    if job.final:
                        if not text.strip():
                            send({"type": "final_empty", "utterance_id": job.utterance_id})
                            continue
                        try:
                            entry = self.save_final(job, text, settings)
                        except Exception as exc:
                            send({"type": "error", "message": str(exc), "recoverable": True})
                            continue
                        if entry:
                            send({"type": "final", "entry": entry, "utterance_id": job.utterance_id})
                            threading.Thread(target=translate, args=(entry,), daemon=True).start()
                    else:
                        event = buffer.accept_partial(job, text)
                        if event:
                            send(event)
                            queue_partial_translation(event)
            finally:
                send({"type": "ready_to_stop"})
                worker_done.set()

        try:
            first = connection.recv(timeout=6)
            if not isinstance(first, str):
                connection.close(code=1008, reason="start message required")
                return
            message = json.loads(first)
            if message.get("type") != "start" or not secrets.compare_digest(str(message.get("token") or ""), self.token):
                connection.close(code=1008, reason="invalid session token")
                return
            settings = self._settings(message)
            if not settings["session_id"]:
                connection.close(code=1008, reason="session id required")
                return
            settings["elapsed"] = settings["base_elapsed"]
            worker_thread = threading.Thread(target=worker, name="caption-decoder", daemon=True)
            worker_thread.start()
            send({"type": "ready", "sample_rate": 16000})

            for incoming in connection:
                if isinstance(incoming, bytes):
                    buffer.feed(incoming, settings["elapsed"])
                    settings["elapsed"] += len(incoming) / 2 / 16000
                    work_ready.set()
                    continue
                command = json.loads(incoming)
                kind = command.get("type")
                if kind == "commit":
                    buffer.commit(float(command.get("elapsed") or settings["elapsed"]))
                    work_ready.set()
                elif kind == "ping":
                    send({"type": "pong", "at": time.time()})
                elif kind == "stop":
                    buffer.close(float(command.get("elapsed") or settings["elapsed"]))
                    stopped.set()
                    work_ready.set()
                    worker_done.wait(30)
                    return
        except Exception as exc:
            if not stopped.is_set():
                send({"type": "error", "message": str(exc), "recoverable": True})
        finally:
            stopped.set()
            buffer.close(settings.get("elapsed", 0.0))
            work_ready.set()
