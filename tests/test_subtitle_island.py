#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
script = (root / "subtitle-window.js").read_text(encoding="utf-8")
markup = (root / "subtitle.html").read_text(encoding="utf-8")
style = (root / "subtitle.css").read_text(encoding="utf-8")
app = (root / "app.js").read_text(encoding="utf-8")
index = (root / "index.html").read_text(encoding="utf-8")

# The preferred shell is a real OS-managed media Picture-in-Picture window.
assert "pictureInPictureEnabled" in script
assert "requestPictureInPicture" in script
assert "captureStream(15)" in script
assert "Picture-in-Picture closed before it became visible" in script
assert "failedImmediately" in script
assert "pipCanvas.width = 1440" in script
assert "pipCanvas.height = 264" in script

# Document PiP is retained as a secondary system surface, followed by the
# in-page draggable island. A normal browser popup must never be used.
assert "documentPictureInPicture" in script
assert "requestWindow({width: 720, height: 132})" in script
assert "window.open('/subtitle.html'" not in script
assert "popup,width" not in script
assert "createEmbeddedFallback" in script
assert "subtitle-island-fallback" in script
assert "class-interpreter-subtitle-drag-start" in script
assert "class-interpreter-subtitle-drag-move" in script

# One shared renderer/state contract, with retained state and a postMessage
# fallback when BroadcastChannel is unavailable.
for key in ("entryId", "englishState", "chineseState", "connected", "recording", "updatedAt"):
    assert key in script
assert "BroadcastChannel" in script
assert "class-interpreter-subtitle-state-request" in script
assert "postMessage" in script
assert "localStorage" in script
assert "preferences" in script
assert "languageMode: 'english'" in script
assert "setLanguageMode" in script
assert "setTheme" in script
assert ':root[data-theme="light"]' in style

# The dedicated fallback page is only a shell; it does not own audio or a
# second streaming connection.
assert "data-subtitle-window" in markup
assert "subtitle-window.js" in markup
assert "getUserMedia" not in markup
assert "WebSocket" not in markup

# Golden-reference geometry and accessibility requirements.
assert "width: min(720px, 100%)" in style
assert "min-height: 92px" in style
assert "border-radius: 34px" in style
assert "font-size: calc(18px * var(--subtitle-scale))" in style
assert "font-size: calc(14px * var(--subtitle-scale))" in style
assert "prefers-reduced-motion" in style
assert "prefers-contrast: more" in style
assert "aria-live=\"polite\"" in script
assert "aria-label=\"Subtitle appearance\"" in script

# English remains current; matching IDs gate late Chinese display.
assert "state.lastCaption?.entryId === message.entry.id" in app
assert "englishState" in app and "chineseState" in app
assert "subtitlewindowchange" in app
assert "aria-pressed=\"false\"" in index
assert "0.3.3-island5" in index

print("subtitle_island ok")
