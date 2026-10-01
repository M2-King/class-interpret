# Streaming Subtitles Implementation Plan

Status: Phase 1 implemented
Created: 2026-10-01
Target: Class Interpreter after v0.3.3
Platforms: Windows and macOS

## 1. Objective

Turn the current batch transcription flow into a near-live bilingual subtitle
experience while preserving the existing notes, course, summary, export, model,
and installer features.

The finished experience should:

- show provisional English while the lecturer is still speaking;
- stabilize and save accurate English without duplicating words;
- show a fast Chinese preview and replace it with a better translation when
  available;
- provide a compact floating subtitle window;
- keep working offline after models are installed;
- use online translation only as an optional quality upgrade;
- avoid an ever-growing processing queue when a laptop is slow.

## 2. Current Bottlenecks

The existing flow is intentionally batch-oriented:

1. `app.js` collects up to eight seconds of 16 kHz audio.
2. The browser creates a complete WAV file.
3. The WAV is sent through an HTTP POST request.
4. Faster Whisper decodes with `beam_size=5` and `best_of=5`.
5. Argos translates the completed English text.
6. Only the final entry is returned to the browser.

This means the perceived delay is mostly local batching and inference time, not
network ping. Reducing the HTTP timeout or changing CSS cannot solve it.

The current Argos English-to-Chinese model also has known quality limitations.
Translation output is not validated, so model contamination such as RTF-like
commands can be displayed as ordinary text.

## 3. Scope

### In scope

- continuous PCM audio streaming;
- voice activity detection and phrase boundaries;
- partial, stable, and final transcript states;
- bounded queues and adaptive performance;
- contextual/glossary-aware recognition;
- provisional and corrected Chinese translation;
- translation output validation;
- floating bilingual subtitle window;
- latency instrumentation;
- Windows and macOS packaging;
- fallback to the current v0.3.3 batch flow.

### Out of scope for the first release

- speaker diarization;
- phone-to-laptop remote streaming;
- replacing the notes/summary database;
- requiring a dedicated GPU;
- bundling every Whisper or translation model;
- a complete Electron, Tauri, or PyQt application rewrite.

## 4. Architecture Decision

Use the streaming concepts and protocol patterns from WhisperLiveKit while
preserving the existing Class Interpreter application.

Do not replace the whole backend in one change. Add a sibling WebSocket service
for live audio and keep the current HTTP server for pages, sessions, notes,
summary, export, model installation, and compatibility.

```text
Microphone / shared tab audio
          |
          | PCM16, 16 kHz mono, 20-40 ms frames
          v
Browser AudioWorklet
          |
          | WebSocket ws://127.0.0.1:8766/live
          v
Streaming session + VAD + bounded audio ring buffer
          |
          v
Stable-prefix Faster Whisper processor
       /                 \
partial English       stable/final English
       |                    |
       |                    +--> save session entry
       |                    +--> translation pipeline
       v                              |
main UI + subtitle window             +--> offline preview
                                      +--> online correction
```

### Why this shape

- The current CTranslate2 Faster Whisper models remain usable.
- The existing local HTTP application remains stable.
- Streaming can be disabled independently.
- A failure in the WebSocket service can fall back to batch transcription.
- The installer does not need a full desktop-runtime rewrite.

## 5. Upstream References

### WhisperLiveKit

Repository: <https://github.com/QuentinFuxa/WhisperLiveKit>

Use as the primary reference for:

- native WebSocket audio transport;
- VAD/VAC behavior;
- LocalAgreement stable-prefix commits;
- incremental full/diff result semantics;
- terminology context;
- adaptive pacing and bounded session state.

WhisperLiveKit is Apache-2.0. Any copied or substantially adapted source must be
isolated, attributed, and distributed with its required notice/license text.

Do not initially select its SimulStreaming policy. The currently bundled model
is CTranslate2-only, while that policy may require compatible PyTorch decoder
weights. Begin with LocalAgreement and Faster Whisper.

### SimulStreaming

Repository: <https://github.com/ufal/SimulStreaming>

Keep as a later benchmark/research option. Its best configuration is too heavy
to make the first cross-platform CPU-friendly default.

### Sublume

Repository: <https://github.com/moonstarsky37/Sublume>

Use as a UX and process-isolation reference for:

- an always-on-top bilingual overlay;
- keeping model inference away from the UI thread;
- replacing an ASR worker cleanly when the model changes;
- bounded audio queues.

Do not import PyQt into the first release. The existing browser UI can provide a
lighter overlay first.

## 6. Proposed Files

### New files

- `audio-worklet.js`
  - captures mono audio without deprecated `ScriptProcessorNode`;
  - downsamples to 16 kHz;
  - emits PCM16 frames;
  - contains no networking or application state.

- `streaming_server.py`
  - starts the local WebSocket server on `127.0.0.1:8766`;
  - authenticates local sessions with a short per-launch token;
  - owns connection lifecycle and protocol validation;
  - never binds to a public interface by default.

- `streaming_hub.py`
  - owns model reuse, VAD, rolling audio buffers, stable-prefix state,
    backpressure, and metrics;
  - exposes a small interface independent of WebSocket implementation.

- `translation_hub.py`
  - translates stable clauses;
  - applies course glossary/context;
  - selects online/offline translation;
  - validates and sanitizes output;
  - emits provisional and final revisions.

- `subtitle-window.js`
  - creates and synchronizes the floating subtitle display;
  - supports Document Picture-in-Picture when available;
  - falls back to a small popup window;
  - never captures microphone audio itself.

- `subtitle.html`
  - minimal accessible subtitle document used by the popup fallback.

- `subtitle.css`
  - transparent/dark/light subtitle presentation;
  - scalable type and two-line bilingual layout.

- `tests/test_streaming_hub.py`
- `tests/test_translation_hub.py`
- `tests/test_streaming_protocol.py`
- `tests/fixtures/streaming/`

### Modified files

- `app.js`
  - replace the default eight-second batching path with streaming;
  - retain batch mode as a fallback;
  - manage partial/stable/final UI state;
  - broadcast subtitle state to the floating window.

- `index.html`
  - add the Subtitle Window button and live-quality controls.

- `style.css`
  - style provisional text, corrected text, connection state, and controls.

- `server.py`
  - start/stop the streaming service with the application;
  - retain existing HTTP APIs;
  - accept finalized transcript entries from `streaming_hub.py`.

- `start.ps1`, `bootstrap.sh`, and launchers
  - start both local services;
  - wait for both health checks;
  - stop both services cleanly.

- `requirements.txt`
  - add a pinned WebSocket dependency;
  - add only dependencies required by the selected VAD implementation.

- packaging and installer tests
  - include the new static/Python files;
  - verify offline startup and repair behavior.

## 7. Streaming Protocol

### Connection

```text
ws://127.0.0.1:8766/live?token=<launch-token>
```

The service must reject non-local origins unless explicitly enabled in a future
LAN mode.

### Client start message

```json
{
  "type": "start",
  "protocol": 1,
  "session_id": "session-id",
  "sample_rate": 16000,
  "format": "pcm_s16le",
  "language": "en",
  "target_language": "zh-CN",
  "model": "small",
  "glossary": "truth table, Boolean algebra, Karnaugh map"
}
```

After the start message, the client sends binary PCM frames. A frame should
normally contain 20-40 ms of audio. The server must accept larger frames up to a
documented maximum for scheduling jitter.

### Server messages

#### Ready

```json
{"type":"ready","protocol":1,"session_id":"session-id"}
```

#### Partial transcript

```json
{
  "type": "partial",
  "utterance_id": "u-42",
  "revision": 3,
  "text": "you do not have the tedious mechanical job",
  "stable_prefix": "you do not have",
  "started_at": 128.4,
  "latency_ms": 760
}
```

Partial text replaces the previous partial for the same `utterance_id`; it is
not appended to the saved transcript.

#### Stable/final transcript

```json
{
  "type": "final",
  "utterance_id": "u-42",
  "revision": 7,
  "text": "You do not have the tedious mechanical job of forming the truth table, so you can use your creativity.",
  "started_at": 128.4,
  "ended_at": 134.1,
  "latency_ms": 1650
}
```

Only final text becomes a permanent session entry.

#### Translation revision

```json
{
  "type": "translation",
  "utterance_id": "u-42",
  "revision": 2,
  "text": "你不必进行绘制真值表这种枯燥的机械工作，因此可以发挥创造力。",
  "quality": "final",
  "provider": "deepseek",
  "latency_ms": 920
}
```

`quality` is `provisional` or `final`. A higher revision replaces an earlier
translation for the same utterance.

#### Status, metrics, and errors

```json
{"type":"status","state":"listening"}
```

```json
{
  "type":"metrics",
  "capture_to_partial_ms":720,
  "capture_to_final_ms":1680,
  "translation_ms":910,
  "queue_audio_ms":120,
  "realtime_factor":0.42
}
```

```json
{"type":"error","code":"MODEL_TOO_SLOW","recoverable":true,"message":"Switching to Small for live mode."}
```

### Protocol rules

- All messages carry a monotonically increasing revision where replacement is
  possible.
- Old revisions must be ignored by the browser.
- The browser reconnects with exponential backoff capped at five seconds.
- Reconnection starts a new utterance; it must never duplicate committed text.
- Audio buffering is bounded. The server must not accumulate unlimited delay.
- If the processor cannot remain near real time, it reduces decode cost or asks
  the user to select a smaller model.

## 8. Recognition Strategy

### Model lifecycle

- Load the selected model once per live session.
- Reuse the existing model cache and `whisper_hub.py` path resolution.
- Keep one inference operation active at a time per model/device.
- Warm the model with a short silent buffer before reporting `ready`.

### VAD and segmentation

- Maintain a small rolling pre-speech buffer so first syllables are not lost.
- Begin an utterance when speech crosses the configured threshold.
- Produce partial updates while speech continues.
- Finalize after an adaptive silence interval, initially 550-800 ms.
- Cap utterance length and cut only at stable word boundaries.

### Stable-prefix policy

- Decode overlapping rolling windows.
- Confirm words only when consecutive hypotheses agree.
- Keep an unstable tail that the UI may revise.
- Feed committed context and course terminology into the next decode.
- Never save unstable words to course notes.

### Decode profiles

#### Live profile

- Small model by default;
- low beam count for provisional updates;
- VAD enabled;
- frequent partial updates;
- bounded context window.

#### Accuracy profile

- Medium model when measured real-time factor permits;
- fewer updates with more context;
- optional final refinement after the utterance closes.

Large v3 remains available for capable hardware but must not be selected
automatically without a benchmark.

## 9. Translation Strategy

### Translation tiers

1. Translate stable clauses, never raw 20-40 ms fragments.
2. If offline mode is enabled, Argos may provide a provisional translation.
3. If DeepSeek cloud is available, request a contextual final translation in
   parallel.
4. Replace the provisional translation only when the final result passes
   validation.
5. If every translation fails, retain the English and show a non-blocking
   translation status instead of fabricated Chinese.

### Translation context

The request should include:

- the current stable English clause;
- up to two previous finalized English sentences;
- course title;
- course glossary/keywords;
- instruction to return plain Chinese text only;
- instruction to preserve equations, code, abbreviations, and proper nouns.

The response must be constrained by size and time. It must not include Markdown,
HTML, explanations, pronunciation notes, or alternative translations.

### Output validation

Reject or sanitize output containing suspicious formatting or contamination,
including:

- RTF controls such as `\\fn`, `\\fs`, `\\bord`, `\\shad`, `\\3c`, and
  `\\4c`;
- RTF groups beginning with `{\\`;
- HTML/script tags;
- null/control characters other than ordinary whitespace;
- an excessive punctuation or symbol ratio;
- repeated tokens/phrases beyond a configured threshold;
- output that is empty, implausibly long, or mostly identical to an English
  source when Chinese was requested.

On rejection:

1. retry the online translator once with a strict repair prompt;
2. fall back to a clean offline result if available;
3. otherwise show `译文正在确认` and keep the English visible;
4. record a local diagnostic without storing API secrets or lecture audio.

All UI rendering must continue to use text nodes/`textContent`, never raw
translation HTML.

## 10. Floating Subtitle Window

### Opening behavior

- Add `字幕窗 / Subtitle Window` near the live controls.
- Prefer Document Picture-in-Picture where the browser exposes it.
- Fall back to `window.open()` with a compact dedicated page.
- If neither is available, provide an in-page detachable subtitle panel.
- Only the main page owns the microphone and WebSocket connection.

### State synchronization

Use one shared subtitle state object:

```json
{
  "connection": "listening",
  "utterance_id": "u-42",
  "english": "forming the truth table",
  "english_state": "partial",
  "chinese": "绘制真值表",
  "chinese_state": "final",
  "latency_ms": 1830
}
```

For a separate popup, synchronize through `BroadcastChannel` and retain a
`postMessage` fallback. Closing the subtitle window must not stop recording.

### Controls

- English only, Chinese only, or bilingual;
- font size;
- line count;
- background opacity;
- dark/light/high-contrast style;
- show/hide timestamps;
- lock controls/auto-hide toolbar;
- remember position and preferences locally;
- clear indicator for provisional text;
- reconnecting and slow-device indicators.

### Rendering rules

- Prefer one current utterance rather than a scrolling transcript.
- Keep stable words visually steady.
- Fade or underline the unstable tail instead of moving the entire line.
- Limit line width and avoid covering the whole lecture screen.
- Never speak the provisional Chinese with text-to-speech.

## 11. Latency and Reliability Targets

Targets must be measured on representative Windows CPU, Windows NVIDIA, Intel
Mac, and Apple Silicon hardware.

### Product targets

- first English partial: p50 <= 1.0 s, p95 <= 2.0 s;
- stable English: p50 <= 2.0 s, p95 <= 3.5 s;
- provisional Chinese: p50 <= 2.5 s;
- corrected online Chinese: p50 <= 4.0 s;
- audio queue: normally below 500 ms;
- reconnect after local server restart: <= 5 s;
- no committed duplicate words across reconnects or rolling windows;
- no unbounded growth in memory, audio queue, transcript revisions, or logs.

These are goals, not promises for every CPU. The UI should report when hardware
cannot sustain the selected model in real time.

### Adaptive behavior

- Measure real-time factor continuously.
- If RTF exceeds 0.8 for several updates, reduce provisional decode cost.
- If RTF exceeds 1.0, stop accumulating delay and recommend/switch to Small.
- Preserve a short recent buffer; never process minutes-old audio as if live.
- Perform online translation independently so network slowness cannot block
  English subtitles.

## 12. Compatibility and Fallback

The existing `/api/sessions/<id>/chunks` endpoint remains available during the
rollout.

Fallback triggers include:

- WebSocket dependency unavailable;
- streaming service health check failed;
- browser lacks AudioWorklet;
- repeated protocol errors;
- model cannot stay close to real time;
- user explicitly selects compatibility mode.

Fallback must show a clear message such as:

> Live mode is unavailable. Continuing with reliable eight-second segments.

The app must not silently stop recording.

## 13. Security and Privacy

- Bind both services to loopback by default.
- Generate a random per-launch WebSocket token.
- Validate Origin and message size.
- Cap audio frame, start-message, and glossary sizes.
- Reject malformed JSON and unsupported binary formats.
- Never send lecture audio to translation providers.
- Send only finalized text when online translation is enabled.
- Do not log API keys, full authorization headers, or raw audio.
- Keep cloud translation clearly labelled in Settings.

## 14. Testing Plan

### Unit tests

- PCM frame validation and resampling;
- VAD state transitions;
- rolling buffer trimming;
- LocalAgreement stable-prefix behavior;
- overlap and duplicate removal;
- revision ordering;
- bounded queue behavior;
- glossary/context limits;
- translation sanitizer and retry rules;
- RTF/HTML/control-code rejection;
- adaptive model/profile decisions.

### Protocol tests

- valid start and binary frame flow;
- invalid token/origin;
- malformed and oversized messages;
- partial-to-final sequence;
- translation revision sequence;
- reconnect without duplicate committed text;
- backpressure under deliberately slow inference;
- clean stop and application shutdown.

### Audio fixtures

Include short, redistributable fixtures covering:

- clean English lecture speech;
- accented English;
- background classroom noise;
- long speech without pauses;
- short interjections;
- equations and abbreviations;
- technical phrases such as `truth table`, `Boolean algebra`, and `Karnaugh
  map`;
- silence and non-speech audio.

### Translation fixtures

- incomplete clauses;
- technical terminology;
- equations and code;
- deliberately contaminated RTF output;
- repeated-token output;
- online timeout;
- offline-only mode;
- provisional-to-final replacement.

### Visual/browser tests

- Chrome and Edge on Windows;
- Chrome on macOS;
- Safari fallback behavior;
- Document Picture-in-Picture path;
- popup fallback path;
- browser refresh while recording;
- subtitle window close/reopen;
- font scaling and long bilingual lines;
- dark, light, and high-contrast modes.

### Packaging tests

- clean Windows install;
- Windows repair over v0.3.3;
- clean Mac install;
- Mac repair preserving models/data;
- offline restart after first install;
- firewall prompt avoidance through loopback-only binding;
- both health endpoints;
- graceful service shutdown;
- recovery ZIP includes every new source/static file.

## 15. Delivery Milestones

### Milestone 0 — Instrument current latency

- Add capture, queue, inference, translation, and total latency metrics.
- Record baseline results for Small and Medium on available hardware.
- No user-visible behavior change.

Exit gate: repeatable baseline and a saved benchmark fixture.

### Milestone 1 — Floating subtitle window on current batch flow

- Add subtitle state model.
- Add Document Picture-in-Picture/popup window.
- Display existing finalized entries only.
- Add preferences and accessibility controls.

Exit gate: opening/closing the window never interrupts recording.

### Milestone 2 — WebSocket audio transport

- Add AudioWorklet and local WebSocket service.
- Stream PCM frames and emit connection/metric events.
- Keep existing eight-second endpoint as automatic fallback.

Exit gate: one-hour streaming soak test with bounded memory and no lost stop
event.

### Milestone 3 — Partial and stable English

- Add VAD and LocalAgreement-style stable prefixes.
- Add partial/stable/final UI rendering.
- Add adaptive performance and queue limits.
- Save final text only.

Exit gate: latency targets met on at least one CPU-only reference laptop and no
duplicate words in fixtures.

### Milestone 4 — Translation quality pipeline

- Add `translation_hub.py`.
- Add contextual DeepSeek translation.
- Keep Argos as a labelled provisional/offline fallback.
- Add contamination detection, retry, and replacement revisions.

Exit gate: no contaminated fixture reaches the UI and terminology tests pass.

### Milestone 5 — Cross-platform hardening

- Tune Windows and macOS startup/shutdown.
- Complete browser matrix.
- Verify installers and recovery tools.
- Add notices for incorporated upstream code.
- Run lesson-length soak tests.

Exit gate: release candidate passes all packaging, recovery, latency, and visual
tests.

## 16. Commit/Review Sequence

Keep reviews small and reversible:

1. metrics and benchmark fixtures;
2. subtitle state plus floating window;
3. AudioWorklet plus protocol types/tests;
4. WebSocket service lifecycle;
5. VAD and bounded buffers;
6. stable-prefix recognition;
7. session persistence integration;
8. translation validation;
9. contextual online translation;
10. adaptive performance;
11. packaging and release assets.

Every step must preserve the batch fallback until the streaming release has
completed cross-platform soak testing.

## 17. Definition of Done

The feature is complete only when:

- subtitles begin before an eight-second segment ends;
- partial text can revise without creating duplicate notes;
- finalized text persists in the current course/session format;
- the floating window can be reopened without touching the microphone;
- English stays live when online translation is unavailable;
- translation contamination is never rendered;
- technical glossary terms are preserved in fixture tests;
- queues and memory remain bounded for a two-hour lecture;
- Windows and macOS installers preserve existing data/models;
- batch mode remains available as a tested fallback;
- all adopted upstream code has compatible licensing and attribution;
- release notes clearly label online/offline behavior and hardware expectations.

## 18. Open Decisions Before Coding

Resolve these with a short prototype/benchmark, not assumptions:

1. Use a minimal `websockets` service on port 8766 or migrate the HTTP server to
   one async framework.
2. Select Silero VAD versus a smaller non-Torch VAD for the default package.
3. Determine whether Medium can remain real time on the reference Windows CPU.
4. Choose the stable-prefix parameters and silence threshold from lecture audio.
5. Confirm Document Picture-in-Picture behavior in the supported Windows/macOS
   browsers and define the Safari fallback.
6. Decide whether provisional Argos Chinese is helpful enough to show by
   default, given its known English-to-Chinese quality limitations.
7. Set cloud translation timeout/cost limits and the exact privacy disclosure.

No production implementation should begin until Milestone 0 answers the
hardware and latency questions above.
