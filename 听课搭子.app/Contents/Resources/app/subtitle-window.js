(function () {
  const CHANNEL_NAME = 'class-interpreter-subtitles';
  const STORAGE_KEY = 'class-interpreter-subtitle-preferences';
  const standalone = document.documentElement.hasAttribute('data-subtitle-window');
  const channel = 'BroadcastChannel' in window ? new BroadcastChannel(CHANNEL_NAME) : null;
  let target = null;
  let targetKind = '';
  let embedded = null;
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
      stylesheet.href = '/subtitle.css?v=0.3.3-island';
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

  function removeEmbeddedFallback() {
    embedded?.remove();
    embedded = null;
    emitWindowState(Boolean(target && !target.closed), targetKind);
  }

  async function open() {
    if (target && !target.closed) {
      target.focus();
      return {kind: targetKind};
    }
    if (embedded?.isConnected) return {kind: 'embedded'};

    if ('documentPictureInPicture' in window) {
      try {
        target = await window.documentPictureInPicture.requestWindow({width: 720, height: 132});
        targetKind = 'picture-in-picture';
        mount(target.document);
        target.addEventListener('pagehide', clearTarget, {once: true});
        emitWindowState(true, targetKind);
        return {kind: targetKind};
      } catch {
        target = null;
        targetKind = '';
      }
    }

    target = window.open('/subtitle.html', 'classInterpreterSubtitles', 'popup,width=720,height=165,resizable=yes');
    if (target) {
      targetKind = 'popup';
      emitWindowState(true, targetKind);
      return {kind: targetKind};
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
  }

  function close() {
    try { target?.close(); } catch {}
    clearTarget();
    removeEmbeddedFallback();
  }

  function isOpen() {
    return Boolean((target && !target.closed) || embedded?.isConnected);
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
      } else if (message.type === 'surface-closed' && !standalone && targetKind === 'popup') {
        clearTarget();
      }
    });
  }

  if (standalone) {
    const start = () => {
      mount(document);
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
      } else if (event.data?.type === 'class-interpreter-subtitle-state-request') {
        try { event.source?.postMessage({type: 'subtitle-state', payload: last}, {targetOrigin: location.origin}); }
        catch {
          try { event.source?.postMessage({type: 'subtitle-state', payload: last}, location.origin); } catch {}
        }
      }
    });
    window.SubtitleWindow = {open, close, publish, isOpen};
  }

  if (standalone) {
    window.addEventListener('message', event => {
      if (event.origin !== location.origin || event.data?.type !== 'subtitle-state') return;
      last = normalizeState(event.data.payload);
      render(document, last);
    });
  }
})();
