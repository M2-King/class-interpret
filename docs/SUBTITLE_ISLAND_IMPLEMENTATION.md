# Subtitle Island Implementation Plan

Status: Implemented and verified
Created: 2026-10-02
Target: Class Interpreter after v0.3.3
Platforms: Windows and macOS
Backend impact: None

## 1. Decision

Implement the compact subtitle experience as a browser-native **media
Picture-in-Picture island** rendered from a live canvas. Retain Document
Picture-in-Picture as a secondary system surface and use a draggable in-page
island as the final fallback. Never open a normal browser popup.

Do not introduce Electron, Tauri, PyQt, or another native desktop shell in this
phase. The subtitle state and rendering should remain portable so a Tauri shell
can replace only the window layer later if browser limitations become a proven
problem.

This decision gives the project:

- an always-on-top subtitle window without a browser address bar in supported
  Chromium browsers;
- a small change surface using the existing HTML, CSS, and JavaScript;
- no new backend API or audio-processing path;
- no large runtime added to the installer;
- the same subtitle presentation on Windows and macOS;
- a safe fallback when Picture-in-Picture is unavailable.

## 2. Problem Statement

The current floating subtitle page is opened as a normal browser window. Its
minimum size, browser address bar, page-like header, and large empty area make it
feel like a second application rather than a subtitle overlay.

The target experience is the supplied golden reference:

- one compact horizontal pill near the top of the screen;
- translucent black surface with a quiet border and shadow;
- small live indicator and product label;
- English as the primary line;
- Chinese as a smaller secondary line when it is ready;
- a subtle waveform/status indicator on the right;
- no permanent toolbar, large waiting message, or empty canvas.

## 3. Goals

- Open a compact, always-on-top subtitle surface with one click.
- Match the golden reference closely without copying operating-system branding.
- Keep the newest English subtitle visible at all times.
- Show Chinese only when it belongs to the same finalized English utterance.
- Collapse naturally when Chinese is unavailable or late.
- Keep microphone capture, streaming, sessions, and translation in the main app.
- Never expose a browser address bar or page-sized popup as a subtitle surface.
- Keep the release package effectively the same size.

## 4. Non-Goals

- No transcription or translation backend changes.
- No native executable or system-level overlay in this phase.
- No Electron runtime.
- No Tauri/Rust build pipeline yet.
- No click-through overlay or global keyboard shortcut in the first version.
- No scrolling transcript inside the island.
- No course controls, summary controls, or settings panel inside the island.

## 5. Window Strategy

### 5.1 Preferred path: media Picture-in-Picture

Render the current island state to a `1440 x 264` canvas, publish it as a small
video stream, and request standard media Picture-in-Picture. The operating
system owns this window, so it is always-on-top, draggable, resizable, and has
no browser address bar.

The Picture-in-Picture document should:

- contain only the island renderer;
- load the dedicated subtitle stylesheet;
- have a transparent page background;
- hide overflow;
- receive subtitle state from the main page;
- close independently without stopping the lesson;
- restore the button state when the user closes it manually.

The app must create this window only from a direct user gesture, because browser
policies require it.

### 5.2 Secondary path: Document Picture-in-Picture

If standard media Picture-in-Picture is unavailable, use Document
Picture-in-Picture with the interactive HTML island. This path must still be
opened directly from the user's click.

### 5.3 Last fallback: in-page island

If both system window paths fail, render the island at the top center of the
main page. Its label row is a drag handle, it remains closable, and it must not
cover the primary recording controls.

## 6. Island States

### Closed

No overlay exists. Recording and transcript behavior are unchanged.

### Ready

- Size: approximately `280 x 48`.
- Green status dot.
- Label: `Class Interpreter`.
- Status: `Ready` or `Waiting for speech…`.
- No Chinese placeholder.

### Listening / partial English

- Width: responsive from `420` to `720` pixels.
- English appears immediately as the primary line.
- Provisional English may use slightly reduced opacity.
- Chinese line remains absent, rather than displaying a large waiting message.
- Waveform animates subtly while audio is active.

### Final English, Chinese pending

- Final English uses full opacity.
- A small muted status may say `Translating…` beside the product label.
- Do not reserve a full-height blank Chinese row.
- If a newer English partial arrives, it becomes the visible subtitle
  immediately.

### Bilingual

- English line: primary, approximately `18px`, medium weight.
- Chinese line: secondary, approximately `14px`, normal weight, 75-82% opacity.
- Chinese is rendered only when its `entryId` matches the currently displayed
  finalized English entry.
- A late translation for an older entry updates the transcript but never
  replaces the current island content.

### English-only fallback

- English remains fully usable when Chinese is slow, unavailable, or rejected.
- The island does not show a large error message.
- Translation failures are reported non-blockingly in the main application.

### Reconnecting / error

- Keep the last safe English subtitle visible.
- Change the status dot to amber.
- Show a short status such as `Reconnecting…` in the label row.
- Do not expand the island for diagnostic text.

## 7. Visual Specification

### Container

- Maximum width: `720px`.
- Minimum practical width: `420px` while active.
- Ready-state width: approximately `280px`.
- Active minimum height: `88px`; maximum typical height: `132px`.
- Border radius: `28-34px`.
- Background: translucent near-black, approximately 82-90% opacity.
- Border: one pixel, low-contrast white/gray.
- Shadow: soft and wide, without a bright glow.
- Backdrop blur may be used when supported, with an opaque fallback.

### Layout

```text
[live dot]  Class Interpreter                         [waveform]
            Primary English subtitle
            Secondary Chinese translation
```

- Left and right padding: `28-34px`.
- Product/status row remains visually quiet.
- Waveform is decorative and must use `aria-hidden="true"`.
- Text is left-aligned for lecture readability.
- The island must not display the local URL or an internal server status.

### Text behavior

- English: maximum two lines.
- Chinese: maximum two lines.
- Prefer natural wrapping over horizontal scrolling.
- Long content uses a subtle bottom fade or line clamp.
- Never shrink below accessible reading sizes merely to fit one line.
- Use system fonts already available on Windows and macOS.

### Hidden controls

On pointer hover or keyboard focus, reveal a small control strip containing:

- decrease/increase text size;
- English-only / bilingual toggle;
- background opacity toggle;
- close.

Controls auto-hide after inactivity. Their appearance must not change the
window's outer dimensions.

## 8. Subtitle State Contract

Keep one canonical state object owned by the main page:

```json
{
  "mode": "listening",
  "entryId": "entry-id-or-empty",
  "english": "Current English subtitle",
  "englishState": "partial",
  "chinese": "",
  "chineseState": "pending",
  "connected": true,
  "recording": true,
  "updatedAt": 0
}
```

Rules:

- `englishState` is `waiting`, `partial`, or `final`.
- `chineseState` is `hidden`, `pending`, `provisional`, or `final`.
- Partial English clears the visible Chinese from the previous entry.
- A translation update is shown only when its `entryId` matches the visible
  finalized English entry.
- Every update replaces the current island state; it is not appended.
- The transcript/session remains the permanent history.

## 9. Synchronization

The main application remains the only owner of:

- microphone or shared-tab capture;
- WebSocket connection;
- session persistence;
- transcription and translation events;
- start/stop recording state.

The island is display-only.

Use this order for synchronization:

1. Direct canvas render for media Picture-in-Picture.
2. Direct renderer call for Document Picture-in-Picture.
3. `BroadcastChannel` for the HTML fallback synchronization.
4. `postMessage` as a fallback for browsers without `BroadcastChannel`.

When an island opens, immediately publish the current retained state so it does
not remain blank until the next spoken word.

## 10. File-Level Implementation

### `subtitle-window.js`

- Add capability detection for media and Document Picture-in-Picture.
- Render the active subtitle state into the media Picture-in-Picture canvas.
- Create and retain exactly one island window.
- Build the island document and copy/load `subtitle.css`.
- Publish retained subtitle state.
- Handle both Picture-in-Picture lifecycle events.
- Fall back without interrupting recording.
- Store presentation preferences in `localStorage`.

### `subtitle.html`

- Reduce markup to the shared island structure.
- Remove page-style header and large empty layout.
- Retain accessible live regions.
- Remain usable as the draggable in-page fallback.

### `subtitle.css`

- Replace the full-page card with the pill/island visual system.
- Add ready, listening, translating, bilingual, and reconnecting states.
- Add responsive width and bounded-height behavior.
- Add reduced-motion and high-contrast support.
- Make popup and Picture-in-Picture rendering visually consistent.

### `app.js`

- Publish the canonical island state for waiting, partial, final, translation,
  reconnecting, stopped, and error events.
- Ensure old translation events never replace newer English.
- Keep English visible when Chinese misses its latency budget.
- Update the button label/state when the island opens or closes.

### `index.html`

- Keep one clearly labelled `Floating subtitles` control.
- Add a short capability tooltip only when fallback mode is used.

### `style.css`

- Style the active/open state of the floating subtitle button.
- Do not duplicate island rules here; island styling belongs in
  `subtitle.css`.

### Backend and packaging

- No Python endpoint or WebSocket protocol changes.
- No new runtime dependency.
- Ensure existing packaging scripts continue including the subtitle files.
- Rebuild Windows, macOS, recovery, and documentation packages after tests.

## 11. Implementation Sequence

### Phase 1 — Shared state and renderer

- Normalize the island state contract.
- Refactor the existing popup renderer into a reusable renderer.
- Preserve current popup behavior during the refactor.

Exit gate: existing popup displays waiting, partial, final, and translated
states without regressions.

### Phase 2 — Picture-in-Picture shell

- Add capability detection.
- Open the Picture-in-Picture window from the existing button.
- Copy styles and mount the shared renderer.
- Restore current state immediately after opening.

Exit gate: opening or closing the island never affects recording.

### Phase 3 — Golden-reference styling

- Implement the compact pill geometry and typography.
- Add state indicator and waveform.
- Add bilingual/English-only responsive layouts.
- Add hover/focus controls without increasing outer size.

Exit gate: visual comparison passes at common Windows display scaling levels
and macOS Retina scale.

### Phase 4 — Fallbacks and persistence

- Add the in-page fallback.
- Remember font, opacity, and language layout preferences.
- Handle refresh, close, and reopen behavior.

Exit gate: both system window paths and the in-page fallback show the same
current subtitle state.

### Phase 5 — Packaging and release

- Run browser and accessibility checks.
- Rebuild Windows and macOS packages.
- Verify repair installs preserve data and models.
- Replace release assets only after acceptance tests pass.

## 12. Browser and Platform Behavior

### Windows

- Primary target: current Chrome and Edge.
- Test 100%, 125%, 150%, and 200% display scaling.
- Verify the Picture-in-Picture window remains above a shared browser tab.
- Confirm closing the island does not close the main local application.

### macOS

- Primary target: current Chrome.
- Test standard and Retina displays.
- Verify window behavior across Spaces/full-screen applications.
- Safari uses the popup or in-page fallback unless Document
  Picture-in-Picture support is confirmed.

## 13. Accessibility

- Use a polite live region for subtitle changes.
- Do not announce every provisional revision when changes are extremely
  frequent.
- All hidden controls must be keyboard reachable.
- Maintain sufficient contrast over the translucent background.
- Respect `prefers-reduced-motion` by disabling waveform animation.
- Respect browser text zoom.
- Do not communicate listening/error state through color alone.

## 14. Performance Requirements

- Opening the island must not restart audio capture or transcription.
- Rendering an update should not allocate an unbounded history.
- At most one external subtitle window may exist.
- Waveform animation must be CSS-only and inexpensive.
- The island must add no material transcription latency.
- Installer growth should be negligible because no runtime is added.

## 15. Test Plan

### Functional

- Open before recording.
- Open during recording.
- Close and reopen during recording.
- Stop/restart a lesson while the island remains open.
- Partial English updates continuously.
- Final English stabilizes correctly.
- Chinese appears only for the matching English entry.
- Slow/failed Chinese never hides current English.
- Reconnection retains the last safe subtitle.

### Visual

- Ready state has no large empty region.
- English-only state collapses the unused Chinese row.
- Bilingual state matches the golden hierarchy.
- Long English and Chinese text clamp cleanly.
- Controls appear on hover/focus and do not resize the island.
- High DPI and browser zoom do not crop text.

### Compatibility

- Document Picture-in-Picture path in Chrome/Edge on Windows.
- Document Picture-in-Picture path in Chrome on macOS.
- Media Picture-in-Picture path.
- Document Picture-in-Picture fallback.
- In-page fallback.
- Browser refresh and island lifecycle.

### Regression

- Main-page subtitle preview still works.
- Recording continues after island close.
- Notes and translations remain saved.
- No duplicate microphone or WebSocket connection.
- Existing installer and recovery tests pass.

## 16. Acceptance Criteria

The feature is complete when:

- the preferred window has no browser address bar;
- the ready island is no larger than necessary;
- the active island normally stays within `720 x 132` CSS pixels;
- English appears immediately and remains the priority;
- Chinese appears only when current and never blocks English;
- the island can close/reopen without interrupting the lesson;
- unsupported browsers automatically use a working fallback;
- no backend behavior or protocol changes are required;
- no large new runtime is added to either installer;
- Windows and macOS packages pass their existing release tests.

## 17. Native Island Reconsideration Gate

Reconsider a Tauri-based native overlay only if testing proves that the browser
approach cannot satisfy one or more of these requirements:

- reliable always-on-top behavior during full-screen lessons;
- acceptable window chrome on the supported browser matrix;
- remembered placement across launches;
- global shortcut support;
- click-through behavior;
- consistent multi-monitor behavior.

If the gate is reached, retain the same island state contract and renderer. The
native project should host the existing subtitle UI rather than duplicate the
transcription or translation pipeline.

## 18. Implementation Record

Implemented on 2026-10-02 with no backend or streaming-protocol changes.

Delivered:

- canonical retained subtitle state in `app.js`;
- shared renderer and lifecycle controller in `subtitle-window.js`;
- media Picture-in-Picture preferred shell;
- Document Picture-in-Picture and draggable in-page iframe fallbacks;
- golden-reference island styling in `subtitle.css`;
- ready, partial English, translating, bilingual, compatibility, saved, and
  reconnecting states;
- persistent font size, bilingual/English-only, and opacity controls;
- stale-translation protection based on matching entry IDs;
- active-state feedback on the main-page subtitle button;
- reduced-motion, increased-contrast, keyboard, and live-region support;
- a bilingual visual fixture and island contract test;
- rebuilt Windows, macOS, recovery, and documentation packages.

Verification completed:

- JavaScript syntax checks;
- all Python test modules;
- API/static asset checks;
- rendered ready and bilingual visual inspection;
- browser console warning/error inspection;
- packaging and site tests after rebuilding release archives.
