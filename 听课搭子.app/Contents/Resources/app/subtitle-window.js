(function () {
  const CHANNEL_NAME = 'class-interpreter-subtitles';
  const STORAGE_KEY = 'class-interpreter-subtitle-preferences';
  const standalone = document.documentElement.hasAttribute('data-subtitle-window');
  const channel = 'BroadcastChannel' in window ? new BroadcastChannel(CHANNEL_NAME) : null;
  let target = null;
  let targetKind = '';
  let embedded = null;
  let embeddedDrag = null;
  let pipCanvas = null;
  let pipVideo = null;
  let pipStream = null;
  let pipFrame = 0;
  let pipOpenedAt = 0;
  let pipClosing = false;
  let lastSize = '';
  let preferences = loadPreferences();
  let last = normalizeState({mode: 'ready', connected: true, recording: false});

  function loadPreferences() {
    try {
      return {
        fontScale: 1,
        languageMode: 'bilingual',
        surface: 'glass',
        ...JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
      };
    } catch {
      return {fontScale: 1, languageMode: 'bilingual', surface: 'glass'};
    }
  }

  function savePreferences() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences)); } catch {}
    channel?.postMessage({type: 'preferences', preferences});
  }

  function normalizeState(payload = {}) {
    const english = String(payload.english || '');
    const chinese = String(payload.chinese || '');
    const englishState = payload.englishState || (payload.partial ? 'partial' : english ? 'final' : 'waiting');
    const mode = payload.mode || (!payload.connected ? 'reconnecting' : payload.recording || english ? 'listening' : 'ready');
    const chineseState = payload.chineseState || (chinese ? 'final' : englishState === 'final' ? 'pending' : 'hidden');
    return {
      mode,
      entryId: String(payload.entryId || ''),
      english,
      englishState,
      chinese,
      chineseState,
      connected: payload.connected !== false,
      recording: Boolean(payload.recording),
      partial: englishState === 'partial',
      updatedAt: Number(payload.updatedAt || Date.now())
    };
  }

  function ensureHead(documentRef) {
    if (!documentRef.querySelector('meta[name="viewport"]')) {
      const viewport = documentRef.createElement('meta');
      viewport.name = 'viewport';
      viewport.content = 'width=device-width,initial-scale=1';
      documentRef.head.appendChild(viewport);
    }
    documentRef.title = 'Class Interpreter Subtitles';
    if (!documentRef.querySelector('link[data-subtitle-style]')) {
      const stylesheet = documentRef.createElement('link');
      stylesheet.rel = 'stylesheet';
      stylesheet.href = '/subtitle.css?v=0.3.3-island2';
      stylesheet.dataset.subtitleStyle = 'true';
      documentRef.head.appendChild(stylesheet);
    }
  }

  function islandMarkup() {
    return `
      <main class="subtitle-island" id="subtitle-island" aria-label="Live subtitles">
        <div class="island-meta">
          <span class="live-dot" aria-hidden="true"></span>
          <span class="product-name">Class Interpreter</span>
          <span class="island-status" id="subtitle-status">Ready</span>
          <span class="waveform" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></span>
          <nav class="island-controls" aria-label="Subtitle appearance">
            <button type="button" data-subtitle-action="smaller" aria-label="Decrease subtitle size">A−</button>
            <button type="button" data-subtitle-action="larger" aria-label="Increase subtitle size">A+</button>
            <button type="button" data-subtitle-action="language" aria-label="Toggle bilingual subtitles">中</button>
            <button type="button" data-subtitle-action="surface" aria-label="Toggle background opacity">◐</button>
            <button type="button" data-subtitle-action="close" aria-label="Close subtitle window">×</button>
          </nav>
        </div>
        <section class="subtitle-copy" aria-live="polite" aria-atomic="true">
          <p id="subtitle-en" class="subtitle-en">Waiting for speech…</p>
          <p id="subtitle-zh" class="subtitle-zh" hidden></p>
        </section>
      </main>`;
  }

  function mount(documentRef) {
    if (!documentRef) return;
    ensureHead(documentRef);
    if (!documentRef.getElementById('subtitle-island')) {
      documentRef.body.innerHTML = islandMarkup();
      documentRef.body.classList.add('subtitle-surface');
      documentRef.querySelectorAll('[data-subtitle-action]').forEach(button => {
        button.addEventListener('click', () => handleAction(documentRef, button.dataset.subtitleAction));
      });
    }
    render(documentRef, last);
  }

  function statusLabel(payload) {
    if (payload.mode === 'compatibility') return 'Compatibility';
    if (!payload.connected || payload.mode === 'reconnecting') return 'Reconnecting…';
    if (payload.chineseState === 'pending' && payload.englishState === 'final') return 'Translating…';
    if (payload.englishState === 'partial') return 'Listening…';
    if (payload.recording) return 'Live';
    if (payload.english) return 'Saved';
    return 'Ready';
  }

  function render(documentRef, payload) {
    if (!documentRef?.body) return;
    const island = documentRef.getElementById('subtitle-island');
    if (!island) return;
    const english = documentRef.getElementById('subtitle-en');
    const chinese = documentRef.getElementById('subtitle-zh');
    const status = documentRef.getElementById('subtitle-status');
    const showChinese = preferences.languageMode === 'bilingual' && Boolean(payload.chinese);
    const ready = !payload.english && !payload.recording;

    documentRef.body.dataset.mode = payload.mode;
    documentRef.body.dataset.englishState = payload.englishState;
    documentRef.body.dataset.chineseState = payload.chineseState;
    documentRef.body.classList.toggle('is-disconnected', !payload.connected);
    documentRef.body.classList.toggle('is-solid', preferences.surface === 'solid');
    island.classList.toggle('is-ready', ready);
    island.classList.toggle('is-bilingual', showChinese);
    island.style.setProperty('--subtitle-scale', String(preferences.fontScale));

    if (status) status.textContent = statusLabel(payload);
    if (english) english.textContent = payload.english || 'Waiting for speech…';
    if (chinese) {
      chinese.textContent = showChinese ? payload.chinese : '';
      chinese.hidden = !showChinese;
    }
    const languageButton = documentRef.querySelector('[data-subtitle-action="language"]');
    if (languageButton) {
      const bilingual = preferences.languageMode === 'bilingual';
      languageButton.classList.toggle('active', bilingual);
      languageButton.setAttribute('aria-pressed', String(bilingual));
      languageButton.title = bilingual ? 'Bilingual subtitles on' : 'English only';
    }
    const surfaceButton = documentRef.querySelector('[data-subtitle-action="surface"]');
    if (surfaceButton) surfaceButton.setAttribute('aria-pressed', String(preferences.surface === 'solid'));
    resizeWindow(documentRef, ready, showChinese);
  }

  function resizeWindow(documentRef, ready, bilingual) {
    const view = documentRef.defaultView;
    if (!view || view.frameElement) return;
    const size = ready ? '320x72' : bilingual ? '720x132' : '720x106';
    if (lastSize === size) return;
    lastSize = size;
    const [width, height] = size.split('x').map(Number);
    try { view.resizeTo(width, height); } catch {}
  }

  function handleAction(documentRef, action) {
    if (action === 'smaller') preferences.fontScale = Math.max(0.85, Number(preferences.fontScale || 1) - 0.1);
    if (action === 'larger') preferences.fontScale = Math.min(1.3, Number(preferences.fontScale || 1) + 0.1);
    if (action === 'language') preferences.languageMode = preferences.languageMode === 'bilingual' ? 'english' : 'bilingual';
    if (action === 'surface') preferences.surface = preferences.surface === 'solid' ? 'glass' : 'solid';
    if (action === 'close') {
      if (documentRef.defaultView?.frameElement) {
        window.parent.postMessage({type: 'class-interpreter-subtitle-close'}, location.origin);
      } else {
        documentRef.defaultView?.close();
      }
      return;
    }
    savePreferences();
    render(documentRef, last);
  }

  function emitWindowState(open, kind = '') {
    if (!standalone) {
      window.dispatchEvent(new CustomEvent('subtitlewindowchange', {detail: {open, kind}}));
    }
  }

  function drawRoundedRect(context, x, y, width, height, radius) {
    context.beginPath();
    context.moveTo(x + radius, y);
    context.arcTo(x + width, y, x + width, y + height, radius);
    context.arcTo(x + width, y + height, x, y + height, radius);
    context.arcTo(x, y + height, x, y, radius);
    context.arcTo(x, y, x + width, y, radius);
    context.closePath();
  }

  function fitCanvasText(context, value, maxWidth) {
    const text = String(value || '');
    if (context.measureText(text).width <= maxWidth) return text;
    let low = 0;
    let high = text.length;
    while (low < high) {
      const middle = Math.ceil((low + high) / 2);
      if (context.measureText(`${text.slice(0, middle)}…`).width <= maxWidth) low = middle;
      else high = middle - 1;
    }
    return `${text.slice(0, low)}…`;
  }

  function ensureMediaPictureInPicture() {
    if (pipCanvas && pipVideo) return;
    pipCanvas = document.createElement('canvas');
    pipCanvas.width = 1440;
    pipCanvas.height = 264;
    pipCanvas.setAttribute('aria-hidden', 'true');
    pipCanvas.style.cssText = 'position:fixed;left:-2px;bottom:-2px;width:1px;height:1px;opacity:.001;pointer-events:none';

    pipVideo = document.createElement('video');
    pipVideo.muted = true;
    pipVideo.autoplay = true;
    pipVideo.playsInline = true;
    pipVideo.disablePictureInPicture = false;
    pipVideo.setAttribute('aria-hidden', 'true');
    pipVideo.style.cssText = 'position:fixed;left:-2px;bottom:-2px;width:1px;height:1px;opacity:.001;pointer-events:none';
    pipStream = pipCanvas.captureStream(15);
    pipVideo.srcObject = pipStream;
    pipVideo.addEventListener('leavepictureinpicture', () => {
      const failedImmediately = !pipClosing
        && targetKind === 'system-picture-in-picture'
        && performance.now() - pipOpenedAt < 1200;
      if (pipFrame) cancelAnimationFrame(pipFrame);
      pipFrame = 0;
      if (targetKind === 'system-picture-in-picture') targetKind = '';
      if (failedImmediately) {
        createEmbeddedFallback();
      } else {
        emitWindowState(Boolean(embedded?.isConnected), embedded?.isConnected ? 'embedded' : '');
      }
    });
    document.body.append(pipCanvas, pipVideo);
  }

  function drawMediaIsland(payload = last, timestamp = performance.now()) {
    if (!pipCanvas) return;
    const context = pipCanvas.getContext('2d');
    const scale = 2;
    const width = pipCanvas.width / scale;
    const height = pipCanvas.height / scale;
    const fontScale = Number(preferences.fontScale || 1);
    const showChinese = preferences.languageMode === 'bilingual' && Boolean(payload.chinese);
    const disconnected = !payload.connected || payload.mode === 'reconnecting';
    const live = payload.recording || payload.englishState === 'partial';
    const primary = payload.english || 'Waiting for speech…';

    context.setTransform(scale, 0, 0, scale, 0, 0);
    context.clearRect(0, 0, width, height);
    context.save();

    const surface = context.createLinearGradient(0, 0, width, height);
    surface.addColorStop(0, preferences.surface === 'solid' ? '#111718' : 'rgba(13,18,19,.98)');
    surface.addColorStop(1, '#090d0e');
    context.shadowColor = 'rgba(0,0,0,.58)';
    context.shadowBlur = 20;
    context.shadowOffsetY = 8;
    drawRoundedRect(context, 8, 8, width - 16, height - 16, 38);
    context.fillStyle = surface;
    context.fill();
    context.shadowColor = 'transparent';
    context.strokeStyle = 'rgba(169,188,188,.34)';
    context.lineWidth = 1;
    context.stroke();

    context.beginPath();
    context.arc(29, 30, 5, 0, Math.PI * 2);
    context.fillStyle = disconnected ? '#f7b955' : '#39e58c';
    context.shadowColor = disconnected ? 'rgba(247,185,85,.45)' : 'rgba(57,229,140,.55)';
    context.shadowBlur = 9;
    context.fill();
    context.shadowColor = 'transparent';

    context.fillStyle = '#dce5e5';
    context.font = '500 12px "Segoe UI", Inter, sans-serif';
    context.textBaseline = 'middle';
    context.fillText('Class Interpreter', 43, 30);
    context.fillStyle = disconnected ? '#f7b955' : '#899696';
    context.font = '500 11px "Segoe UI", Inter, sans-serif';
    context.fillText(statusLabel(payload), 147, 30);

    const phase = timestamp / 165;
    const bars = [8, 16, 24, 13, 20, 10];
    context.lineCap = 'round';
    context.lineWidth = 3;
    context.strokeStyle = disconnected ? '#f7b955' : '#43e694';
    bars.forEach((base, index) => {
      const motion = live ? Math.sin(phase + index * .8) * 5 : 0;
      const barHeight = Math.max(6, base + motion);
      const x = 653 + index * 8;
      context.beginPath();
      context.moveTo(x, 30 - barHeight / 2);
      context.lineTo(x, 30 + barHeight / 2);
      context.stroke();
    });

    context.fillStyle = '#f3f7f7';
    context.font = `600 ${20 * fontScale}px "Segoe UI", Inter, sans-serif`;
    context.fillText(fitCanvasText(context, primary, 658), 28, showChinese ? 72 : 83);
    if (showChinese) {
      context.fillStyle = '#b8c3c3';
      context.font = `400 ${15 * fontScale}px "Microsoft YaHei UI", "PingFang SC", sans-serif`;
      context.fillText(fitCanvasText(context, payload.chinese, 658), 28, 103);
    }
    context.restore();
  }

  function animateMediaIsland() {
    if (pipFrame) cancelAnimationFrame(pipFrame);
    const tick = timestamp => {
      drawMediaIsland(last, timestamp);
      if (document.pictureInPictureElement === pipVideo && last.recording) {
        pipFrame = requestAnimationFrame(tick);
      } else {
        pipFrame = 0;
      }
    };
    pipFrame = requestAnimationFrame(tick);
  }

  function clearTarget() {
    target = null;
    targetKind = '';
    lastSize = '';
    emitWindowState(Boolean(embedded), embedded ? 'embedded' : '');
  }

  function createEmbeddedFallback() {
    if (embedded?.isConnected) return embedded;
    embedded = document.createElement('iframe');
    embedded.src = '/subtitle.html?embedded=1';
    embedded.className = 'subtitle-island-fallback';
    embedded.title = 'Class Interpreter floating subtitles';
    embedded.allow = 'picture-in-picture';
    document.body.appendChild(embedded);
    emitWindowState(true, 'embedded');
    return embedded;
  }

  function beginEmbeddedDrag() {
    if (!embedded?.isConnected) return;
    const rect = embedded.getBoundingClientRect();
    embeddedDrag = {left: rect.left, top: rect.top};
    embedded.style.left = `${rect.left}px`;
    embedded.style.top = `${rect.top}px`;
    embedded.style.transform = 'none';
  }

  function moveEmbeddedDrag(dx, dy) {
    if (!embeddedDrag || !embedded?.isConnected) return;
    const maxLeft = Math.max(8, window.innerWidth - embedded.offsetWidth - 8);
    const maxTop = Math.max(8, window.innerHeight - embedded.offsetHeight - 8);
    embedded.style.left = `${Math.min(maxLeft, Math.max(8, embeddedDrag.left + Number(dx || 0)))}px`;
    embedded.style.top = `${Math.min(maxTop, Math.max(8, embeddedDrag.top + Number(dy || 0)))}px`;
  }

  function removeEmbeddedFallback() {
    embedded?.remove();
    embedded = null;
    emitWindowState(Boolean(target && !target.closed), targetKind);
  }

  async function open() {
    if (document.pictureInPictureElement === pipVideo) return {kind: 'system-picture-in-picture'};
    if (target && !target.closed) {
      target.focus();
      return {kind: targetKind};
    }
    if (embedded?.isConnected) return {kind: 'embedded'};

    if (document.pictureInPictureEnabled && window.HTMLVideoElement && 'requestPictureInPicture' in window.HTMLVideoElement.prototype) {
      try {
        pipClosing = false;
        ensureMediaPictureInPicture();
        drawMediaIsland(last);
        if (pipVideo.paused) await pipVideo.play();
        await pipVideo.requestPictureInPicture();
        pipOpenedAt = performance.now();
        await new Promise(resolve => setTimeout(resolve, 220));
        if (document.pictureInPictureElement !== pipVideo) {
          throw new Error('Picture-in-Picture closed before it became visible');
        }
        targetKind = 'system-picture-in-picture';
        animateMediaIsland();
        emitWindowState(true, targetKind);
        return {kind: targetKind};
      } catch {
        targetKind = '';
      }
    }

    if ('documentPictureInPicture' in window) {
      try {
        target = await window.documentPictureInPicture.requestWindow({width: 720, height: 132});
        targetKind = 'document-picture-in-picture';
        mount(target.document);
        target.addEventListener('pagehide', clearTarget, {once: true});
        emitWindowState(true, targetKind);
        return {kind: targetKind};
      } catch {
        target = null;
        targetKind = '';
      }
    }

    createEmbeddedFallback();
    return {kind: 'embedded'};
  }

  function publish(payload) {
    last = normalizeState({...last, ...payload, updatedAt: Date.now()});
    channel?.postMessage({type: 'subtitle-state', payload: last});
    try { target?.postMessage({type: 'subtitle-state', payload: last}, location.origin); } catch {}
    try { embedded?.contentWindow?.postMessage({type: 'subtitle-state', payload: last}, location.origin); } catch {}
    try { render(target?.document, last); } catch { clearTarget(); }
    drawMediaIsland(last);
    if (document.pictureInPictureElement === pipVideo && last.recording && !pipFrame) animateMediaIsland();
  }

  async function close() {
    if (document.pictureInPictureElement === pipVideo) {
      pipClosing = true;
      try { await document.exitPictureInPicture(); } catch {}
      finally { pipClosing = false; }
    }
    try { target?.close(); } catch {}
    clearTarget();
    removeEmbeddedFallback();
  }

  function isOpen() {
    return Boolean(document.pictureInPictureElement === pipVideo || (target && !target.closed) || embedded?.isConnected);
  }

  if (channel) {
    channel.addEventListener('message', event => {
      const message = event.data || {};
      if (message.type === 'subtitle-state' && standalone) {
        last = normalizeState(message.payload);
        render(document, last);
      } else if (message.type === 'request-state' && !standalone) {
        channel.postMessage({type: 'subtitle-state', payload: last});
      } else if (message.type === 'preferences') {
        preferences = {...preferences, ...message.preferences};
        if (standalone) render(document, last);
      }
    });
  }

  if (standalone) {
    const start = () => {
      mount(document);
      if (window.parent !== window) {
        document.body.dataset.embedded = 'true';
        const handle = document.querySelector('.island-meta');
        let pointerStart = null;
        handle?.addEventListener('pointerdown', event => {
          if (event.target.closest('button')) return;
          pointerStart = {x: event.screenX, y: event.screenY, id: event.pointerId};
          handle.setPointerCapture(event.pointerId);
          window.parent.postMessage({type: 'class-interpreter-subtitle-drag-start'}, location.origin);
        });
        handle?.addEventListener('pointermove', event => {
          if (!pointerStart || event.pointerId !== pointerStart.id) return;
          window.parent.postMessage({
            type: 'class-interpreter-subtitle-drag-move',
            dx: event.screenX - pointerStart.x,
            dy: event.screenY - pointerStart.y
          }, location.origin);
        });
        const finishDrag = event => {
          if (!pointerStart || event.pointerId !== pointerStart.id) return;
          pointerStart = null;
          window.parent.postMessage({type: 'class-interpreter-subtitle-drag-end'}, location.origin);
        };
        handle?.addEventListener('pointerup', finishDrag);
        handle?.addEventListener('pointercancel', finishDrag);
      }
      channel?.postMessage({type: 'request-state'});
      try { window.opener?.postMessage({type: 'class-interpreter-subtitle-state-request'}, location.origin); } catch {}
      if (window.parent !== window) {
        try { window.parent.postMessage({type: 'class-interpreter-subtitle-state-request'}, location.origin); } catch {}
      }
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
    else start();
    window.addEventListener('pagehide', () => channel?.postMessage({type: 'surface-closed'}));
  } else {
    window.addEventListener('message', event => {
      if (event.origin !== location.origin) return;
      if (event.data?.type === 'class-interpreter-subtitle-close') {
        removeEmbeddedFallback();
      } else if (event.data?.type === 'class-interpreter-subtitle-drag-start') {
        beginEmbeddedDrag();
      } else if (event.data?.type === 'class-interpreter-subtitle-drag-move') {
        moveEmbeddedDrag(event.data.dx, event.data.dy);
      } else if (event.data?.type === 'class-interpreter-subtitle-drag-end') {
        embeddedDrag = null;
      } else if (event.data?.type === 'class-interpreter-subtitle-state-request') {
        try { event.source?.postMessage({type: 'subtitle-state', payload: last}, {targetOrigin: location.origin}); }
        catch {
          try { event.source?.postMessage({type: 'subtitle-state', payload: last}, location.origin); } catch {}
        }
      }
    });
    window.SubtitleWindow = {open, close, publish, isOpen};
    if (document.pictureInPictureEnabled && window.HTMLVideoElement && 'requestPictureInPicture' in window.HTMLVideoElement.prototype) {
      ensureMediaPictureInPicture();
      drawMediaIsland(last);
      pipVideo.play().catch(() => {});
    }
  }

  if (standalone) {
    window.addEventListener('message', event => {
      if (event.origin !== location.origin || event.data?.type !== 'subtitle-state') return;
      last = normalizeState(event.data.payload);
      render(document, last);
    });
  }
})();
