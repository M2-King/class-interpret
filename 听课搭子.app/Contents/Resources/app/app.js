const $ = id => document.getElementById(id);
const ui = {
  title: $('class-title'), source: $('source'), model: $('model'), glossary: $('glossary'),
  speak: $('speak'), history: $('history'), heading: $('session-heading'), meta: $('session-meta'),
  indicator: $('record-indicator'), record: $('record-button'), summary: $('summary-button'),
  export: $('export-button'), count: $('entry-count'), transcript: $('transcript'),
  summaryContent: $('summary-content'), summarySource: $('summary-source'),
  status: $('local-status'), notice: $('notice'), recordStatus: $('record-status'),
  elapsed: $('elapsed-time'), concepts: $('concept-list'), conceptCount: $('concept-count'),
  durationMetric: $('duration-metric'), segmentMetric: $('segment-metric'),
  wordMetric: $('word-metric'), conceptMetric: $('concept-metric'),
  micHealth: $('mic-health'), audioHealth: $('audio-health'), engineHealth: $('engine-health'),
  summaryPage: $('summary-page-content'), exportList: $('export-list'),
  exportPreview: $('export-preview'), exportTitle: $('export-title'),
  greeting: $('home-greeting'), currentModel: $('current-model-label'),
  installTranslation: $('install-translation'), quitApp: $('quit-app'),
  modelBanner: $('model-banner'), modelBannerText: $('model-banner-text'),
  installWhisper: $('install-whisper'), installDeepseek: $('install-deepseek'),
  installDeepseekPage: $('install-deepseek-page'),
  deepseekHealth: $('deepseek-health'), deepseekStatusText: $('deepseek-status-text')
};
const state = { session: null, recording: false, stream: null, audioContext: null,
  sourceNode: null, processor: null, silent: null, startedAt: 0, chunks: [], samples: 0,
  uploadQueue: Promise.resolve(), pending: 0, quietSamples: 0, voicedSamples: 0, baseElapsed: 0 };
const RATE = 16000, WINDOW = RATE * 8, OVERLAP = RATE;
const MODEL_LABELS = { small: 'Small', medium: 'Medium', 'large-v3': 'Large v3' };
let clockTimer = null;
let lastStatus = null;

function showView(name) {
  document.querySelectorAll('.view').forEach(view => { view.hidden = view.id !== `view-${name}`; });
  document.querySelectorAll('[data-view]').forEach(button => {
    button.classList.toggle('active', button.dataset.view === name && button.classList.contains('nav-item'));
  });
  if (name === 'live' && ui.notice && !ui.notice.textContent) {
    ui.notice.textContent = '第一次识别会下载免费语音模型，需保持联网；下载完成后可离线使用。';
  }
}

function greeting() {
  const hour = new Date().getHours();
  const text = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  if (ui.greeting) ui.greeting.textContent = text;
}

function syncModelCards() {
  if (!ui.model) return;
  const value = ui.model.value;
  document.querySelectorAll('.model-card').forEach(card => {
    card.classList.toggle('selected', card.dataset.model === value);
  });
  if (ui.currentModel) ui.currentModel.textContent = MODEL_LABELS[value] || value;
}

function formatClock(seconds) {
  seconds = Math.max(0, Math.floor(Number(seconds) || 0));
  return [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60]
    .map(value => String(value).padStart(2, '0')).join(':');
}

function sessionSeconds() {
  const recorded = state.session?.entries?.length ? Number(state.session.entries.at(-1).at) || 0 : 0;
  return state.recording ? state.baseElapsed + (performance.now() - state.startedAt) / 1000 : recorded;
}

function updateClock() {
  if (ui.elapsed) ui.elapsed.textContent = formatClock(sessionSeconds());
}

function extractConcepts(session) {
  const glossary = ui.glossary.value.split(/[,;\n]/).map(item => item.trim()).filter(Boolean);
  const stop = new Set(['about','after','again','also','because','before','being','between','could','from','have','into','just','more','most','other','some','such','than','that','their','there','these','they','this','through','today','using','very','what','when','where','which','will','with','would','your']);
  const counts = new Map();
  for (const entry of session?.entries || []) {
    const words = (entry.en || '').toLowerCase().match(/[a-z][a-z-]{3,}/g) || [];
    for (const word of words) if (!stop.has(word)) counts.set(word, (counts.get(word) || 0) + 1);
  }
  const frequent = [...counts.entries()].filter(([, count]) => count > 1).sort((a,b) => b[1] - a[1]).map(([word]) => word);
  return [...new Set([...glossary, ...frequent])].slice(0, 10);
}

function renderInsights(session) {
  const entries = session?.entries || [];
  const concepts = extractConcepts(session);
  const words = entries.reduce((total, entry) => total + ((entry.en || '').match(/[A-Za-z]+(?:[-'][A-Za-z]+)*/g) || []).length, 0);
  const minutes = Math.ceil((entries.length ? Number(entries.at(-1).at) || 0 : 0) / 60);
  ui.concepts.replaceChildren();
  if (concepts.length) {
    for (const concept of concepts) { const chip = document.createElement('span'); chip.textContent = concept; ui.concepts.append(chip); }
  } else {
    const empty = document.createElement('span'); empty.className = 'concept-placeholder'; empty.textContent = '术语将从课堂记录中提取'; ui.concepts.append(empty);
  }
  ui.conceptCount.textContent = concepts.length;
  ui.segmentMetric.textContent = entries.length;
  ui.wordMetric.textContent = words;
  ui.conceptMetric.textContent = concepts.length;
  ui.durationMetric.textContent = `${minutes} 分钟`;
  updateClock();
}

function notesText(session) {
  if (!session) return '选择一节课或先开始同传。';
  return [`# ${session.title}`, `创建时间：${session.created}`, '', '## 课堂记录',
    ...session.entries.flatMap(e => [`[${formatTime(e.at)}] ${e.en}`, e.zh || '（中文译文不可用）', '']),
    '## 课后总结', session.summary || '尚未生成'].join('\n');
}

$('mobile-settings').addEventListener('click', () => {
  const expanded = document.querySelector('.sidebar').classList.toggle('expanded');
  $('mobile-settings').setAttribute('aria-expanded', String(expanded));
  $('mobile-settings').textContent = expanded ? '收起' : '菜单';
});

document.querySelectorAll('[data-view]').forEach(button => {
  button.addEventListener('click', () => showView(button.dataset.view));
});

document.querySelectorAll('.model-card').forEach(card => {
  card.addEventListener('click', () => {
    if (ui.model.disabled) return;
    ui.model.value = card.dataset.model;
    syncModelCards();
    if (lastStatus) applyStatus(lastStatus);
  });
});

async function api(path, options = {}) {
  const response = await fetch(path, options);
  let body;
  try { body = await response.json(); } catch { throw new Error('本地服务没有返回有效内容'); }
  if (!response.ok) throw new Error(body.error || `请求失败 (${response.status})`);
  return body;
}

function notice(message, error = false) {
  if (!ui.notice) return;
  ui.notice.textContent = message;
  ui.notice.classList.toggle('error', error === true);
  ui.notice.classList.toggle('warn', error === 'warn');
}

function applyStatus(status) {
  lastStatus = status;
  const whisperReady = !!(status.whisper_models?.[ui.model?.value || 'small'] ?? status.whisper);
  const cloud = !!status.deepseek_cloud;
  const deepseekReady = cloud || !!(status.deepseek_ready || status.deepseek);
  const deepseekLabel = cloud ? (status.deepseek || '云接口') : (status.deepseek || '待安装');
  ui.status.textContent = `v${status.version || '?'} · ${status.translation ? '离线翻译就绪' : '翻译待安装'} · ${whisperReady ? '语音就绪' : '语音模型待下载'} · DeepSeek ${deepseekReady ? deepseekLabel : '待安装'}`;
  if (ui.engineHealth) ui.engineHealth.textContent = whisperReady ? '正常运行' : '语音模型待下载';
  if (ui.deepseekHealth) ui.deepseekHealth.textContent = deepseekReady ? deepseekLabel : '未安装';
  if (ui.deepseekStatusText) {
    if (cloud) {
      ui.deepseekStatusText.textContent = 'DeepSeek 云接口已就绪。点生成课后总结即可使用，不用再装 Ollama。';
    } else {
      ui.deepseekStatusText.textContent = deepseekReady
        ? `本机 DeepSeek 已就绪：${deepseekLabel}。点生成课后总结时会自动使用。`
        : '还没有 DeepSeek。可把 API key 放进 secrets/deepseek.api，或点「安装 DeepSeek」用本机模型。没装也能生成摘录。';
    }
  }
  const needTranslation = !status.translation;
  const needWhisper = !whisperReady;
  const needDeepseek = !deepseekReady;
  if (ui.modelBanner) ui.modelBanner.classList.toggle('show', needTranslation || needWhisper || needDeepseek);
  if (ui.installTranslation) {
    ui.installTranslation.hidden = !needTranslation;
    ui.installTranslation.disabled = !needTranslation;
  }
  if (ui.installWhisper) {
    ui.installWhisper.hidden = !needWhisper;
    ui.installWhisper.disabled = !needWhisper;
  }
  [ui.installDeepseek, ui.installDeepseekPage].forEach(button => {
    if (!button) return;
    button.hidden = !needDeepseek;
    button.disabled = !needDeepseek;
  });
  if (ui.modelBannerText && (needTranslation || needWhisper || needDeepseek)) {
    if (needTranslation && needWhisper) {
      ui.modelBannerText.textContent = '翻译模型和语音模型都还没装好。校园网请换手机热点，再点右侧按钮下载。';
    } else if (needWhisper) {
      ui.modelBannerText.textContent = '语音识别模型还没下载（Small 约 500MB）。校园网经常失败，请换手机热点后点「下载语音模型」。';
    } else if (needTranslation) {
      ui.modelBannerText.textContent = '中文翻译模型还没装好。点右侧按钮下载（需联网，大约一两分钟）。';
    } else {
      ui.modelBannerText.textContent = '课后总结可用本机 DeepSeek（免费，约 1.1GB）。上课同传不需要它；校园网请换手机热点后再装。';
    }
  }
}

function humanizeChunkError(message) {
  if (/ConnectTimeout|timed out|Hub|huggingface|Errno 60|snapshot folder|语音识别模型还没下载/i.test(message)) {
    return message.includes('语音识别模型还没下载')
      ? message
      : '语音模型还没下完。校园网连不上 Hugging Face。请换手机热点，点黄色条「下载语音模型」，建议用 Small。';
  }
  return `这一段录音处理失败：${message}`;
}

function fetchTimeout(ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, cancel: () => clearTimeout(timer) };
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
    empty.innerHTML = '<strong>准备好听课了</strong><p>点击“开始同传”，允许浏览器访问麦克风。</p>';
    ui.transcript.append(empty);
  } else {
    for (const entry of session.entries) ui.transcript.append(makeEntry(entry));
    ui.transcript.scrollTop = ui.transcript.scrollHeight;
  }
  const summary = session?.summary || '点击“生成课后总结”，随时整理已经记录的内容。';
  ui.summaryContent.textContent = summary;
  ui.summaryContent.classList.toggle('muted', !session?.summary);
  if (ui.summaryPage) {
    ui.summaryPage.textContent = session?.summary || 'Your summary will appear here.';
    ui.summaryPage.classList.toggle('muted', !session?.summary);
  }
  ui.summarySource.textContent = session?.summary_source || '尚未生成';
  ui.summary.disabled = !session?.entries.length;
  ui.export.disabled = !session?.entries.length;
  $('summary-page-button').disabled = !session?.entries.length;
  $('export-page-button').disabled = !session;
  if (ui.exportTitle) ui.exportTitle.textContent = session?.title || '当前笔记';
  if (ui.exportPreview) ui.exportPreview.textContent = notesText(session);
  renderInsights(session);
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

function fillSessionList(container, list) {
  container.replaceChildren();
  if (!list.length) {
    container.innerHTML = '<span class="muted">尚无课堂记录</span>';
    return;
  }
  for (const item of list) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = (container === ui.exportList ? 'note-item' : 'history-item') + (state.session?.id === item.id ? ' active' : '');
    const title = document.createElement('strong'); title.textContent = item.title;
    const info = document.createElement('small');
    info.textContent = `${new Date(item.created).toLocaleDateString('zh-CN')} · ${item.count} 条记录`;
    button.append(title, info);
    button.addEventListener('click', async () => {
      if (state.recording) await stopRecording();
      state.session = await api(`/api/sessions/${item.id}`);
      ui.title.value = state.session.title;
      drawSession(); loadHistory();
      if (container === ui.history) showView('live');
    });
    container.append(button);
  }
}

async function loadHistory() {
  const list = await api('/api/sessions');
  fillSessionList(ui.history, list);
  if (ui.exportList) fillSessionList(ui.exportList, list);
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
    } catch (error) { notice(humanizeChunkError(error.message), true); }
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
  ui.indicator.classList.add('active'); ui.recordStatus.textContent = '正在听课';
  ui.micHealth.textContent = '已连接'; ui.audioHealth.textContent = '检测语音中';
  clearInterval(clockTimer); clockTimer = setInterval(updateClock, 1000); updateClock();
  ui.model.disabled = true; ui.source.disabled = true;
  notice(matchMedia('(max-width: 750px)').matches
    ? '正在录音。手机请保持页面在前台并避免锁屏；译文按停顿或约 8 秒更新。'
    : '正在录音。每约 8 秒生成一段译文；首次使用时模型下载会等待较久。');
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
  ui.indicator.classList.remove('active'); ui.recordStatus.textContent = '已结束录音';
  ui.micHealth.textContent = '已断开'; ui.audioHealth.textContent = '等待语音';
  clearInterval(clockTimer); clockTimer = null; updateClock();
  ui.model.disabled = false; ui.source.disabled = false;
  notice('录音已结束，正在完成剩余识别…');
  await state.uploadQueue;
  notice('课堂记录已保存。可修正文字，再点击“生成课后总结”。');
}

ui.record.addEventListener('click', async () => {
  ui.record.disabled = true;
  try { if (state.recording) await stopRecording(); else { showView('live'); await startRecording(); } }
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

document.querySelector('[data-generate-summary]').addEventListener('click', () => ui.summary.click());
$('summary-page-button').addEventListener('click', () => {
  showView('live');
  ui.summary.click();
});
$('export-page-button').addEventListener('click', () => ui.export.click());
$('transcript-search').addEventListener('input', event => {
  const query = event.target.value.trim().toLocaleLowerCase();
  document.querySelectorAll('#transcript .entry').forEach(row => {
    row.hidden = query && !row.textContent.toLocaleLowerCase().includes(query);
  });
});
$('global-search').addEventListener('input', event => {
  const query = event.target.value.trim().toLocaleLowerCase();
  if (!$('view-live').hidden) {
    $('transcript-search').value = event.target.value;
    $('transcript-search').dispatchEvent(new Event('input'));
    return;
  }
  document.querySelectorAll('.history-item, .note-item').forEach(row => {
    row.hidden = query && !row.textContent.toLocaleLowerCase().includes(query);
  });
});

ui.summary.addEventListener('click', async () => {
  if (!state.session) return;
  const sessionId = state.session.id;
  ui.summary.disabled = true; ui.summary.textContent = '正在整理课堂内容…';
  notice('正在生成课后总结；已安装本机 DeepSeek 时会自动使用，否则给出课堂摘录。');
  try {
    await state.uploadQueue;
    const result = await api(`/api/sessions/${sessionId}/summary`, {method:'POST', body: '{}'});
    if (state.session?.id === sessionId) {
      state.session.summary = result.summary; state.session.summary_source = result.source;
      drawSession();
      showView('summarize');
      notice(`课后总结已生成：${result.source}。`);
    }
  } catch (error) { notice(`总结失败：${error.message}`, true); }
  finally { ui.summary.textContent = '生成课程总结'; ui.summary.disabled = !state.session?.entries.length; }
});

ui.export.addEventListener('click', () => {
  const session = state.session; if (!session) return;
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([notesText(session)], {type:'text/plain;charset=utf-8'}));
  link.download = `${session.title.replace(/[\\/:*?"<>|]/g, '_') || '课堂笔记'}.txt`;
  link.click(); setTimeout(() => URL.revokeObjectURL(link.href), 1000);
});

async function init() {
  greeting();
  syncModelCards();
  showView('home');
  drawSession();
  try {
    const [status] = await Promise.all([api('/api/status'), loadHistory()]);
    applyStatus(status);
    if (!status.translation) {
      notice('中文翻译模型还没装好。请看页面上方的黄色提示，点按钮安装。', 'warn');
    } else if (!(status.whisper_models?.[ui.model?.value || 'small'] ?? status.whisper)) {
      notice('语音模型还没下载。请看黄色条，换手机热点后点「下载语音模型」。', 'warn');
    } else if (!(status.deepseek_ready || status.deepseek)) {
      notice('同传已经可以用。课后总结可点「安装 DeepSeek」（免费，约 1.1GB）；不装也能生成摘录。', 'warn');
    }
  } catch (error) {
    if (ui.modelBanner) ui.modelBanner.classList.add('show');
    if (ui.modelBannerText) ui.modelBannerText.textContent = `无法连接本地服务：${error.message}`;
    notice(`无法连接本地服务：${error.message}`, true);
    ui.status.textContent = '服务未就绪';
  }
}

if (ui.installTranslation) {
  ui.installTranslation.addEventListener('click', async () => {
    ui.installTranslation.disabled = true;
    if (ui.modelBannerText) ui.modelBannerText.textContent = '正在下载英语 → 中文模型，请保持联网…';
    notice('正在下载英语 → 中文模型，请保持联网…', 'warn');
    const timeout = fetchTimeout(360000);
    try {
      const body = await api('/api/translation/install', { method: 'POST', signal: timeout.signal });
      timeout.cancel();
      const status = await api('/api/status');
      applyStatus(status);
      if (ui.modelBannerText) {
        ui.modelBannerText.textContent = body.message || '翻译模型已安装。现在可以开始同传。';
      }
      notice(body.message || '翻译模型已安装。现在可以开始同传。', 'warn');
    } catch (error) {
      timeout.cancel();
      const message = error.name === 'AbortError' ? '下载超时，请换网络后重试。' : error.message;
      if (ui.modelBanner) ui.modelBanner.classList.add('show');
      if (ui.modelBannerText) ui.modelBannerText.textContent = `翻译模型安装失败：${message}。可改用手机热点后重试。`;
      notice(`翻译模型安装失败：${message}。可改用手机热点后重试。`, true);
      ui.installTranslation.disabled = false;
    }
  });
}

if (ui.installWhisper) {
  ui.installWhisper.addEventListener('click', async () => {
    ui.installWhisper.disabled = true;
    const model = ui.model?.value || 'small';
    if (ui.modelBannerText) {
      ui.modelBannerText.textContent = `正在下载语音模型 ${model}。校园网请改用手机热点，可能要几分钟…`;
    }
    notice(`正在下载语音模型 ${model}…`, 'warn');
    const timeout = fetchTimeout(600000);
    try {
      const body = await api('/api/whisper/install', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({model}),
        signal: timeout.signal
      });
      timeout.cancel();
      const status = await api('/api/status');
      applyStatus(status);
      notice(body.message || '语音模型已下载。现在可以开始同传。', 'warn');
    } catch (error) {
      timeout.cancel();
      const message = error.name === 'AbortError' ? '下载超时，请换手机热点后重试。' : error.message;
      if (ui.modelBanner) ui.modelBanner.classList.add('show');
      if (ui.modelBannerText) ui.modelBannerText.textContent = `语音模型下载失败：${message}`;
      notice(`语音模型下载失败：${message}`, true);
      ui.installWhisper.disabled = false;
    }
  });
}

async function installDeepseek() {
  const buttons = [ui.installDeepseek, ui.installDeepseekPage].filter(Boolean);
  buttons.forEach(button => { button.disabled = true; });
  const message = '正在安装本机 DeepSeek（Ollama + deepseek-r1:1.5b，约 1.1GB）。校园网请改用手机热点，可能要十几分钟…';
  if (ui.modelBannerText) ui.modelBannerText.textContent = message;
  if (ui.deepseekStatusText) ui.deepseekStatusText.textContent = message;
  notice(message, 'warn');
  const timeout = fetchTimeout(900000);
  try {
    const body = await api('/api/deepseek/install', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({model: 'deepseek-r1:1.5b'}),
      signal: timeout.signal
    });
    timeout.cancel();
    const status = await api('/api/status');
    applyStatus(status);
    notice(body.message || 'DeepSeek 已安装。生成课后总结时会自动使用。', 'warn');
  } catch (error) {
    timeout.cancel();
    const text = error.name === 'AbortError' ? '下载超时，请换手机热点后重试。' : error.message;
    if (ui.modelBanner) ui.modelBanner.classList.add('show');
    if (ui.modelBannerText) ui.modelBannerText.textContent = `DeepSeek 安装失败：${text}`;
    if (ui.deepseekStatusText) ui.deepseekStatusText.textContent = `DeepSeek 安装失败：${text}`;
    notice(`DeepSeek 安装失败：${text}`, true);
    buttons.forEach(button => { button.disabled = false; });
  }
}

if (ui.installDeepseek) ui.installDeepseek.addEventListener('click', installDeepseek);
if (ui.installDeepseekPage) ui.installDeepseekPage.addEventListener('click', installDeepseek);

if (ui.quitApp) {
  ui.quitApp.addEventListener('click', async () => {
    try { await api('/api/shutdown', { method: 'POST' }); }
    catch { /* service may already be gone */ }
    notice('听课搭子已退出。可以关闭这个标签页。');
    ui.status.textContent = '服务已退出';
  });
}

init();
