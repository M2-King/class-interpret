const $ = id => document.getElementById(id);
const ui = {
  title: $('class-title'), source: $('source'), model: $('model'), glossary: $('glossary'),
  speak: $('speak'), history: $('history'), heading: $('session-heading'), meta: $('session-meta'),
  indicator: $('record-indicator'), record: $('record-button'), summary: $('summary-button'),
  export: $('export-button'), count: $('entry-count'), transcript: $('transcript'),
  summaryContent: $('summary-content'), summarySource: $('summary-source'),
  status: $('local-status'), notice: $('notice')
};
const state = { session: null, recording: false, stream: null, audioContext: null,
  sourceNode: null, processor: null, silent: null, startedAt: 0, chunks: [], samples: 0,
  uploadQueue: Promise.resolve(), pending: 0, quietSamples: 0, voicedSamples: 0, baseElapsed: 0 };
const RATE = 16000, WINDOW = RATE * 8, OVERLAP = RATE;

async function api(path, options = {}) {
  const response = await fetch(path, options);
  let body;
  try { body = await response.json(); } catch { throw new Error('本地服务没有返回有效内容'); }
  if (!response.ok) throw new Error(body.error || `请求失败 (${response.status})`);
  return body;
}

function notice(message, error = false) {
  ui.notice.textContent = message;
  ui.notice.classList.toggle('error', error);
}

function formatTime(seconds) {
  seconds = Math.floor(Number(seconds) || 0);
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

function drawSession() {
  const session = state.session;
  ui.heading.textContent = session ? session.title : '准备开始听课';
  ui.meta.textContent = session ? `创建于 ${new Date(session.created).toLocaleString('zh-CN')} · 自动保存` : '选择声音来源，开始后将自动保存课堂记录。';
  ui.count.textContent = `${session?.entries.length || 0} 条`;
  ui.transcript.replaceChildren();
  if (!session?.entries.length) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.innerHTML = '<div class="empty-icon">◌</div><strong>准备好听课了</strong><p>点击“开始同传”，允许浏览器访问麦克风。</p>';
    ui.transcript.append(empty);
  } else {
    for (const entry of session.entries) ui.transcript.append(makeEntry(entry));
    ui.transcript.scrollTop = ui.transcript.scrollHeight;
  }
  ui.summaryContent.textContent = session?.summary || '点击上方“生成课后总结”，随时整理已经记录的内容。';
  ui.summaryContent.classList.toggle('muted', !session?.summary);
  ui.summarySource.textContent = session?.summary_source || '尚未生成';
  ui.summary.disabled = !session?.entries.length;
  ui.export.disabled = !session?.entries.length;
}

function makeEntry(entry) {
  const row = document.createElement('article');
  row.className = 'entry';
  const time = document.createElement('div');
  time.className = 'entry-time';
  time.textContent = formatTime(entry.at);
  const body = document.createElement('div');
  body.className = 'entry-body';
  const en = document.createElement('div');
  en.className = 'entry-en';
  en.textContent = entry.en;
  const zh = document.createElement('div');
  zh.className = 'entry-zh' + (entry.zh ? '' : ' missing');
  zh.textContent = entry.zh || '中文翻译尚不可用，请安装翻译模型。';
  const tools = document.createElement('div');
  tools.className = 'entry-tools';
  const edit = document.createElement('button');
  edit.type = 'button';
  edit.textContent = '修正识别 / 译文';
  edit.addEventListener('click', () => {
    const english = document.createElement('textarea');
    english.className = 'edit-box'; english.value = entry.en; english.setAttribute('aria-label', '英文原文');
    const chinese = document.createElement('textarea');
    chinese.className = 'edit-box'; chinese.value = entry.zh; chinese.setAttribute('aria-label', '中文译文');
    const actions = document.createElement('div'); actions.className = 'edit-actions';
    const save = document.createElement('button'); save.textContent = '保存修改';
    const cancel = document.createElement('button'); cancel.textContent = '取消';
    save.addEventListener('click', async () => {
      try {
        const updated = await api(`/api/sessions/${state.session.id}/entries/${entry.id}`, {
          method: 'PATCH', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({en: english.value, zh: chinese.value})
        });
        Object.assign(entry, updated);
        state.session.summary = ''; state.session.summary_source = '';
        drawSession(); notice('已保存修正。课后总结会根据修正后的文字生成。');
      } catch (error) { notice(error.message, true); }
    });
    cancel.addEventListener('click', drawSession);
    actions.append(save, cancel);
    body.replaceChildren(english, chinese, actions);
  });
  tools.append(edit); body.append(en, zh, tools); row.append(time, body);
  return row;
}

async function loadHistory() {
  const list = await api('/api/sessions');
  ui.history.replaceChildren();
  if (!list.length) { ui.history.innerHTML = '<span class="muted">尚无课堂记录</span>'; return; }
  for (const item of list) {
    const button = document.createElement('button');
    button.className = 'history-item' + (state.session?.id === item.id ? ' active' : '');
    const title = document.createElement('strong'); title.textContent = item.title;
    const info = document.createElement('small');
    info.textContent = `${new Date(item.created).toLocaleDateString('zh-CN')} · ${item.count} 条记录`;
    button.append(title, info);
    button.addEventListener('click', async () => {
      if (state.recording) await stopRecording();
      state.session = await api(`/api/sessions/${item.id}`);
      ui.title.value = state.session.title;
      drawSession(); loadHistory();
    });
    ui.history.append(button);
  }
}

async function ensureSession() {
  if (state.session) return;
  state.session = await api('/api/sessions', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({title: ui.title.value.trim() || `课堂 ${new Date().toLocaleDateString('zh-CN')}`})
  });
  drawSession(); loadHistory();
}

function downsample(input, sampleRate) {
  const ratio = sampleRate / RATE;
  const length = Math.floor(input.length / ratio);
  const output = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const start = Math.floor(i * ratio), end = Math.max(start + 1, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < Math.min(end, input.length); j++) sum += input[j];
    output[i] = sum / (end - start);
  }
  return output;
}

function wav(samples) {
  const buffer = new ArrayBuffer(44 + samples.length * 2), view = new DataView(buffer);
  const put = (offset, string) => { for (let i = 0; i < string.length; i++) view.setUint8(offset + i, string.charCodeAt(i)); };
  put(0, 'RIFF'); view.setUint32(4, buffer.byteLength - 8, true); put(8, 'WAVE');
  put(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, RATE, true);
  view.setUint32(28, RATE * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  put(36, 'data'); view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const value = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, value < 0 ? value * 32768 : value * 32767, true);
  }
  return new Blob([buffer], {type: 'audio/wav'});
}

function flatten(chunks, length) {
  const data = new Float32Array(length); let offset = 0;
  for (const part of chunks) { data.set(part, offset); offset += part.length; }
  return data;
}

function queueAudio(samples, elapsed) {
  const sessionId = state.session.id;
  const model = ui.model.value;
  const glossary = ui.glossary.value;
  const blob = wav(samples);
  state.pending++;
  if (state.pending > 3) notice(`识别正在追赶录音，当前有 ${state.pending} 段待处理。可切换到更快的模型。`);
  state.uploadQueue = state.uploadQueue.then(async () => {
    try {
      const response = await api(`/api/sessions/${sessionId}/chunks`, {
        method: 'POST',
        headers: {'X-Model': model, 'X-Glossary': encodeURIComponent(glossary), 'X-Elapsed': String(elapsed)},
        body: blob
      });
      if (response.entry && state.session?.id === sessionId) {
        state.session.entries.push(response.entry);
        state.session.summary = ''; state.session.summary_source = '';
        drawSession(); loadHistory();
        if (ui.speak.checked && response.entry.zh && 'speechSynthesis' in window) {
          const speech = new SpeechSynthesisUtterance(response.entry.zh);
          speech.lang = 'zh-CN'; speech.rate = 1.1;
          window.speechSynthesis.speak(speech);
        }
      }
      if (response.translation_error) notice(`已识别英文；中文翻译不可用：${response.translation_error}`, true);
      else if (response.entry) notice('识别与翻译已自动保存。');
    } catch (error) { notice(`这一段录音处理失败：${error.message}`, true); }
    finally { state.pending--; }
  });
}

function flushAudio(final = false, naturalPause = false) {
  if (state.samples < (final ? RATE : naturalPause ? RATE * 3 : WINDOW)) return;
  const data = flatten(state.chunks, state.samples);
  const elapsed = state.baseElapsed + (performance.now() - state.startedAt) / 1000;
  queueAudio(data, elapsed);
  if (final) { state.chunks = []; state.samples = 0; }
  else if (naturalPause) { state.chunks = []; state.samples = 0; }
  else { const tail = data.slice(-OVERLAP); state.chunks = [tail]; state.samples = tail.length; }
  state.quietSamples = 0; state.voicedSamples = 0;
}

async function startRecording() {
  await ensureSession();
  if (!navigator.mediaDevices?.getUserMedia) throw new Error('浏览器不支持录音。请使用较新的 Chrome 或 Edge。');
  if (ui.source.value === 'screen') {
    if (!navigator.mediaDevices.getDisplayMedia) throw new Error('此浏览器不支持共享标签页音频。');
    state.stream = await navigator.mediaDevices.getDisplayMedia({video: true, audio: true});
    if (!state.stream.getAudioTracks().length) {
      state.stream.getTracks().forEach(track => track.stop());
      throw new Error('共享时没有勾选“共享音频”，请重新选择。');
    }
  } else {
    state.stream = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}});
  }
  state.audioContext = new AudioContext();
  state.sourceNode = state.audioContext.createMediaStreamSource(state.stream);
  state.processor = state.audioContext.createScriptProcessor(8192, 1, 1);
  state.silent = state.audioContext.createGain(); state.silent.gain.value = 0;
  state.sourceNode.connect(state.processor); state.processor.connect(state.silent); state.silent.connect(state.audioContext.destination);
  state.chunks = []; state.samples = 0; state.quietSamples = 0; state.voicedSamples = 0;
  state.baseElapsed = state.session.entries.length ? state.session.entries.at(-1).at + 1 : 0;
  state.startedAt = performance.now(); state.recording = true;
  state.processor.onaudioprocess = event => {
    if (!state.recording) return;
    const part = downsample(event.inputBuffer.getChannelData(0), state.audioContext.sampleRate);
    state.chunks.push(part); state.samples += part.length;
    let energy = 0;
    for (const sample of part) energy += sample * sample;
    const quiet = Math.sqrt(energy / part.length) < 0.006;
    if (quiet) state.quietSamples += part.length;
    else { state.voicedSamples += part.length; state.quietSamples = 0; }
    if (state.quietSamples >= RATE * 0.55 && state.voicedSamples >= RATE * 0.6) flushAudio(false, true);
    else flushAudio();
  };
  state.stream.getAudioTracks().forEach(track => track.addEventListener('ended', () => { if (state.recording) stopRecording(); }));
  ui.record.classList.add('recording'); ui.record.lastElementChild.textContent = '结束听课';
  ui.indicator.classList.add('active'); ui.indicator.lastChild.textContent = '正在听课';
  ui.model.disabled = true; ui.source.disabled = true;
  notice('正在录音。每约 8 秒生成一段译文；首次使用时模型下载会等待较久。');
}

async function stopRecording() {
  if (!state.recording) return;
  state.recording = false;
  state.processor.onaudioprocess = null;
  flushAudio(true);
  state.sourceNode.disconnect(); state.processor.disconnect(); state.silent.disconnect();
  state.stream.getTracks().forEach(track => track.stop());
  await state.audioContext.close();
  state.stream = null; state.audioContext = null;
  ui.record.classList.remove('recording'); ui.record.lastElementChild.textContent = '继续同传';
  ui.indicator.classList.remove('active'); ui.indicator.lastChild.textContent = '已结束录音';
  ui.model.disabled = false; ui.source.disabled = false;
  notice('录音已结束，正在完成剩余识别…');
  await state.uploadQueue;
  notice('课堂记录已保存。可修正文字，再点击“生成课后总结”。');
}

ui.record.addEventListener('click', async () => {
  ui.record.disabled = true;
  try { if (state.recording) await stopRecording(); else await startRecording(); }
  catch (error) { notice(`无法开始录音：${error.message}`, true); }
  finally { ui.record.disabled = false; }
});

$('new-session').addEventListener('click', async () => {
  if (state.recording) await stopRecording();
  state.session = null; ui.title.value = '';
  ui.record.lastElementChild.textContent = '开始同传';
  drawSession(); loadHistory();
  notice('新课堂已准备好。输入课程名称后即可开始同传。');
});

ui.summary.addEventListener('click', async () => {
  if (!state.session) return;
  const sessionId = state.session.id;
  ui.summary.disabled = true; ui.summary.textContent = '✦ 正在整理课堂内容…';
  notice('正在生成课后总结；如果已安装本机 DeepSeek，会自动使用。');
  try {
    await state.uploadQueue;
    const result = await api(`/api/sessions/${sessionId}/summary`, {method:'POST', body: '{}'});
    if (state.session?.id === sessionId) {
      state.session.summary = result.summary; state.session.summary_source = result.source;
      drawSession(); $('summary-section').scrollIntoView({behavior:'smooth', block:'start'});
      notice(`课后总结已生成：${result.source}。`);
    }
  } catch (error) { notice(`总结失败：${error.message}`, true); }
  finally { ui.summary.textContent = '✦ 生成课后总结'; ui.summary.disabled = !state.session?.entries.length; }
});

ui.export.addEventListener('click', () => {
  const session = state.session; if (!session) return;
  const content = [`# ${session.title}`, `创建时间：${session.created}`, '', '## 课堂记录', ...session.entries.flatMap(e => [`[${formatTime(e.at)}] ${e.en}`, e.zh || '（中文译文不可用）', '']), '## 课后总结', session.summary || '尚未生成'].join('\n');
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([content], {type:'text/plain;charset=utf-8'}));
  link.download = `${session.title.replace(/[\\/:*?"<>|]/g, '_') || '课堂笔记'}.txt`;
  link.click(); setTimeout(() => URL.revokeObjectURL(link.href), 1000);
});

async function init() {
  drawSession();
  try {
    const [status] = await Promise.all([api('/api/status'), loadHistory()]);
    ui.status.textContent = `${status.translation ? '离线翻译就绪' : '翻译模型待安装'} · ${status.deepseek ? 'DeepSeek 就绪' : '基础总结就绪'}`;
    if (!status.translation) notice('英语 → 中文模型尚未安装。运行 setup_models.py 后即可显示中文译文。', true);
  } catch (error) { notice(`无法连接本地服务：${error.message}`, true); ui.status.textContent = '服务未就绪'; }
}
init();
