(function () {
  const channel = new BroadcastChannel('class-interpreter-subtitles');
  let target = null;
  let last = {status: 'Ready', english: '', chinese: '', partial: false};

  function template(documentRef) {
    documentRef.head.innerHTML = '<meta charset="utf-8"><title>Class Interpreter Subtitles</title><link rel="stylesheet" href="/subtitle.css">';
    documentRef.body.innerHTML = '<main class="subtitle-stage"><header><span class="live-dot"></span><b>CLASS INTERPRETER</b><small id="subtitle-status">Ready</small></header><section><p id="subtitle-en" class="subtitle-en">Waiting for speech…</p><p id="subtitle-zh" class="subtitle-zh">等待课堂语音…</p></section></main>';
    return documentRef;
  }

  function render(documentRef, payload) {
    if (!documentRef) return;
    const status = documentRef.getElementById('subtitle-status');
    const english = documentRef.getElementById('subtitle-en');
    const chinese = documentRef.getElementById('subtitle-zh');
    if (status) status.textContent = payload.status || (payload.partial ? 'Listening…' : 'Live');
    if (english) english.textContent = payload.english || 'Waiting for speech…';
    if (chinese) chinese.textContent = payload.chinese || (payload.partial ? '正在识别…' : '等待翻译…');
    documentRef.body?.classList.toggle('is-partial', Boolean(payload.partial));
  }

  async function open() {
    if (target && !target.closed) {
      target.focus();
      return;
    }
    if ('documentPictureInPicture' in window) {
      target = await window.documentPictureInPicture.requestWindow({width: 900, height: 240});
      template(target.document);
      target.addEventListener('pagehide', () => { target = null; });
    } else {
      target = window.open('/subtitle.html', 'classInterpreterSubtitles', 'popup,width=900,height=260,resizable=yes');
      if (!target) throw new Error('浏览器阻止了字幕窗口，请允许此网站打开弹出窗口。');
    }
    setTimeout(() => render(target?.document, last), 80);
  }

  function publish(payload) {
    last = {...last, ...payload};
    channel.postMessage(last);
    try { render(target?.document, last); } catch { target = null; }
  }

  window.SubtitleWindow = {open, publish};
})();
