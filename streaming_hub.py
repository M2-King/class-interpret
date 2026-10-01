"""Thread-safe state primitives for incremental classroom transcription."""

from __future__ import annotations

import re
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass

RATE = 16000
BYTES_PER_SAMPLE = 2


def pcm_rms(frame: bytes) -> float:
    if len(frame) < 2:
        return 0.0
    usable = len(frame) - (len(frame) % 2)
    total = 0.0
    count = usable // 2
    for index in range(0, usable, 2):
        sample = int.from_bytes(frame[index:index + 2], "little", signed=True) / 32768.0
        total += sample * sample
    return (total / max(1, count)) ** 0.5


def stable_prefix(previous: str, current: str) -> str:
    old = previous.split()
    new = current.split()
    agreed: list[str] = []
    normalize = lambda value: re.sub(r"[^\w']", "", value).casefold()
    for left, right in zip(old, new):
        if normalize(left) != normalize(right):
            break
        agreed.append(right)
    return " ".join(agreed)


@dataclass(frozen=True)
class DecodeJob:
    utterance_id: str
    pcm: bytes
    elapsed: float
    final: bool
    created_at: float


class LiveBuffer:
    """Bounded PCM buffer with replaceable partials and explicit commits."""

    def __init__(
        self,
        *,
        min_partial_seconds: float = 1.0,
        partial_step_seconds: float = 1.0,
        partial_window_seconds: float = 6.0,
        max_seconds: float = 16.0,
    ) -> None:
        self.min_partial_bytes = int(RATE * BYTES_PER_SAMPLE * min_partial_seconds)
        self.partial_step_bytes = int(RATE * BYTES_PER_SAMPLE * partial_step_seconds)
        self.partial_window_bytes = int(RATE * BYTES_PER_SAMPLE * partial_window_seconds)
        self.max_bytes = int(RATE * BYTES_PER_SAMPLE * max_seconds)
        self.lock = threading.RLock()
        self.current = bytearray()
        self.utterance_id = uuid.uuid4().hex
        self.last_partial_size = 0
        self.last_hypothesis = ""
        self.final_jobs: deque[DecodeJob] = deque()
        self.closed = False

    def feed(self, frame: bytes, elapsed: float) -> bool:
        if not frame or len(frame) % 2:
            raise ValueError("PCM frame must contain complete signed 16-bit samples")
        with self.lock:
            if self.closed:
                return False
            self.current.extend(frame)
            if len(self.current) >= self.max_bytes:
                self._commit_locked(elapsed)
                return True
            return False

    def commit(self, elapsed: float) -> bool:
        with self.lock:
            return self._commit_locked(elapsed)

    def _commit_locked(self, elapsed: float) -> bool:
        if len(self.current) < int(RATE * BYTES_PER_SAMPLE * 0.25):
            self.current.clear()
            self.last_partial_size = 0
            self.last_hypothesis = ""
            return False
        self.final_jobs.append(DecodeJob(
            utterance_id=self.utterance_id,
            pcm=bytes(self.current),
            elapsed=max(0.0, float(elapsed)),
            final=True,
            created_at=time.monotonic(),
        ))
        self.current.clear()
        self.utterance_id = uuid.uuid4().hex
        self.last_partial_size = 0
        self.last_hypothesis = ""
        return True

    def next_job(self, elapsed: float) -> DecodeJob | None:
        with self.lock:
            if self.final_jobs:
                return self.final_jobs.popleft()
            size = len(self.current)
            if size < self.min_partial_bytes or size - self.last_partial_size < self.partial_step_bytes:
                return None
            self.last_partial_size = size
            return DecodeJob(
                utterance_id=self.utterance_id,
                # Preview only the newest bounded window. The final pass still
                # receives the entire utterance, so saved notes remain complete.
                pcm=bytes(self.current[-self.partial_window_bytes:]),
                elapsed=max(0.0, float(elapsed)),
                final=False,
                created_at=time.monotonic(),
            )

    def accept_partial(self, job: DecodeJob, text: str) -> dict | None:
        with self.lock:
            if job.final or job.utterance_id != self.utterance_id:
                return None
            value = text.strip()
            if not value:
                return None
            stable = stable_prefix(self.last_hypothesis, value)
            self.last_hypothesis = value
            return {
                "type": "partial",
                "utterance_id": job.utterance_id,
                "text": value,
                "stable_prefix": stable,
                "elapsed": job.elapsed,
                "latency_ms": int((time.monotonic() - job.created_at) * 1000),
            }

    def close(self, elapsed: float) -> None:
        with self.lock:
            self._commit_locked(elapsed)
            self.closed = True

    def pending(self) -> bool:
        with self.lock:
            return bool(self.current or self.final_jobs)
