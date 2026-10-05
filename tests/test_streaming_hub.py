#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from streaming_hub import BYTES_PER_SAMPLE, RATE, LiveBuffer, pcm_rms, stable_prefix

silence = b"\x00\x00" * 320
loud = (12000).to_bytes(2, "little", signed=True) * 320
assert pcm_rms(silence) == 0
assert pcm_rms(loud) > 0.3
assert stable_prefix("forming the truth table", "forming the truth table now") == "forming the truth table"
assert stable_prefix("forming truth", "forming tables") == "forming"

buffer = LiveBuffer(min_partial_seconds=0.1, partial_step_seconds=0.1, max_seconds=2)
frame = loud * 5
buffer.feed(frame, 0.1)
job = buffer.next_job(0.1)
assert job and not job.final
event = buffer.accept_partial(job, "forming the truth")
assert event and event["type"] == "partial"

buffer.feed(frame, 0.2)
job = buffer.next_job(0.2)
assert job and not job.final
event = buffer.accept_partial(job, "forming the truth table")
assert event and event["stable_prefix"] == "forming the truth"

buffer.feed(frame, 0.3)
assert buffer.commit(0.3)
final = buffer.next_job(0.3)
assert final and final.final and len(final.pcm) == len(frame) * 3
assert not buffer.pending()

try:
    buffer.feed(b"\x00", 0.4)
    raise AssertionError("odd PCM frame should fail")
except ValueError:
    pass

short = LiveBuffer()
short.feed(b"\x00\x00" * int(RATE * 0.1), 0.1)
assert not short.commit(0.1)

capped = LiveBuffer(min_partial_seconds=0.1, partial_step_seconds=0.1, partial_window_seconds=0.15)
capped.feed(frame, 0.1)
capped.feed(frame, 0.2)
capped_job = capped.next_job(0.2)
assert capped_job and len(capped_job.pcm) == int(RATE * BYTES_PER_SAMPLE * 0.15)
capped.feed(frame, 0.3)
capped.commit(0.3)
capped_final = capped.next_job(0.3)
assert capped_final and len(capped_final.pcm) == len(frame) * 3

print("streaming_hub ok")
