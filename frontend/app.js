/**
 * app.js — HH Goa 2026 Voice RAG Frontend (Complete PWA)
 *
 * Capabilities:
 *  - PWA Service Worker & Install App prompt support
 *  - Web Audio API real-time microphone waveform visualizer
 *  - MediaRecorder audio capture & POST /api/voice
 *  - Text query input & suggestion chips via POST /api/query
 *  - Web Speech API Text-to-Speech (TTS) audio readout
 *  - Copy to clipboard & settings modal
 *  - Latency breakdown (< 200 ms target) and Grounding badge
 */

'use strict';

/* ══════════════════════════════════════════════════════════════
   1. CONFIG & SETTINGS
══════════════════════════════════════════════════════════════ */

const CONFIG = {
  apiBase: localStorage.getItem('hh_goa_api_base') || '',
  topK: parseInt(localStorage.getItem('hh_goa_top_k'), 10) || 3,
  latencyTargetMs: 200,
};

function getEndpoint(path) {
  const base = CONFIG.apiBase.replace(/\/+$/, '');
  return `${base}${path}`;
}

/* ══════════════════════════════════════════════════════════════
   2. STATE MACHINE
══════════════════════════════════════════════════════════════ */

const State = Object.freeze({
  IDLE:            'IDLE',
  RECORDING:       'RECORDING',
  TRANSCRIBING:    'TRANSCRIBING',
  RETRIEVING:      'RETRIEVING',
  GENERATING:      'GENERATING',
  GROUNDING:       'GROUNDING_CHECK',
  ANSWER:          'ANSWER',
  STT_ERROR:       'STT_ERROR',
  RETRIEVAL_ERROR: 'RETRIEVAL_ERROR',
  GEN_ERROR:       'GENERATION_ERROR',
  NO_CONTEXT:      'INSUFFICIENT_CONTEXT',
  NO_SPEECH:       'NO_SPEECH',
});

let currentState = State.IDLE;

/* ══════════════════════════════════════════════════════════════
   3. DOM REFERENCES
══════════════════════════════════════════════════════════════ */

const DOM = {
  // Mic & Hero
  btnMic:          document.getElementById('btn-mic'),
  micLabel:        document.getElementById('mic-label'),
  canvasVisualizer:document.getElementById('audio-visualizer'),
  statusBar:       document.getElementById('status-bar'),
  statusText:      document.getElementById('status-text'),
  
  // Text Input
  textQueryForm:   document.getElementById('text-query-form'),
  inputTextQuery:  document.getElementById('input-text-query'),
  btnSubmitText:   document.getElementById('btn-submit-text'),
  suggestionChips: document.querySelectorAll('.chip'),
  
  // Results
  resultsWrapper:  document.getElementById('results-wrapper'),
  errorCard:       document.getElementById('error-card'),
  errorText:       document.getElementById('error-text'),
  transcriptCard:  document.getElementById('transcript-card'),
  transcriptText:  document.getElementById('transcript-text'),
  answerCard:      document.getElementById('answer-card'),
  answerText:      document.getElementById('answer-text'),
  groundedBadge:   document.getElementById('grounded-badge'),
  btnSpeakAnswer:  document.getElementById('btn-speak-answer'),
  btnCopyAnswer:   document.getElementById('btn-copy-answer'),
  sourcesSection:  document.getElementById('sources-section'),
  sourcesList:     document.getElementById('sources-list'),
  latencySection:  document.getElementById('latency-section'),
  latencyGrid:     document.getElementById('latency-grid'),

  // Header & Status
  systemStatus:    document.getElementById('system-status'),
  systemStatusText:document.getElementById('system-status-text'),
  btnInstall:      document.getElementById('btn-install'),
  btnSettings:     document.getElementById('btn-settings'),

  // Settings Modal
  settingsModal:   document.getElementById('settings-modal'),
  btnCloseSettings:document.getElementById('btn-close-settings'),
  btnSaveSettings: document.getElementById('btn-save-settings'),
  settingApiUrl:   document.getElementById('setting-api-url'),
  settingTopK:     document.getElementById('setting-top-k'),
  topKVal:         document.getElementById('top-k-val'),
};

/* ══════════════════════════════════════════════════════════════
   4. UI STATE UPDATER
══════════════════════════════════════════════════════════════ */

function setState(s) {
  currentState = s;
  
  const isRecording  = s === State.RECORDING;
  const isProcessing = [State.TRANSCRIBING, State.RETRIEVING, State.GENERATING, State.GROUNDING].includes(s);
  const isDone       = s === State.ANSWER;
  const isError      = [State.STT_ERROR, State.RETRIEVAL_ERROR, State.GEN_ERROR, State.NO_CONTEXT, State.NO_SPEECH].includes(s);

  // Mic Button
  DOM.btnMic.disabled = isProcessing;
  DOM.btnMic.setAttribute('aria-pressed', isRecording ? 'true' : 'false');
  DOM.btnMic.setAttribute('aria-label', isRecording ? 'Stop recording' : 'Start voice recording');
  DOM.btnMic.classList.toggle('recording', isRecording);

  // Mic Label
  if (isError) {
    DOM.micLabel.textContent = 'Tap to try again';
  } else if (isRecording) {
    DOM.micLabel.textContent = 'Listening… tap to stop';
  } else if (isDone) {
    DOM.micLabel.textContent = 'Tap to ask another';
  } else {
    DOM.micLabel.textContent = 'Tap to speak';
  }

  // Status Bar Messages
  const statusMessages = {
    [State.TRANSCRIBING]: 'Transcribing speech…',
    [State.RETRIEVING]:   'Searching MSMARCO-XI index…',
    [State.GENERATING]:   'Generating grounded answer…',
    [State.GROUNDING]:    'Verifying citations & grounding…',
  };

  const msg = statusMessages[s];
  if (msg) {
    DOM.statusText.textContent = msg;
    DOM.statusBar.classList.add('visible');
  } else {
    DOM.statusBar.classList.remove('visible');
  }

  // Error Card
  if (isError && s !== State.NO_CONTEXT) {
    DOM.errorCard.style.display = 'block';
  } else {
    DOM.errorCard.style.display = 'none';
  }

  // Results Container
  if (isDone || isError) {
    DOM.resultsWrapper.style.display = 'flex';
  }
}

/* ══════════════════════════════════════════════════════════════
   5. STAGE CYCLING SIMULATION DURING FAST CALLS
══════════════════════════════════════════════════════════════ */

let _stageTimers = [];

function startStageCycle() {
  stopStageCycle();
  const stages = [
    { state: State.TRANSCRIBING, delay: 0 },
    { state: State.RETRIEVING,   delay: 500 },
    { state: State.GENERATING,   delay: 1200 },
    { state: State.GROUNDING,    delay: 2400 },
  ];
  stages.forEach(({ state, delay }) => {
    const t = setTimeout(() => {
      if ([State.TRANSCRIBING, State.RETRIEVING, State.GENERATING, State.GROUNDING].includes(currentState)) {
        setState(state);
      }
    }, delay);
    _stageTimers.push(t);
  });
}

function stopStageCycle() {
  _stageTimers.forEach(clearTimeout);
  _stageTimers = [];
}

/* ══════════════════════════════════════════════════════════════
   6. REAL-TIME AUDIO VISUALIZER (Web Audio API)
══════════════════════════════════════════════════════════════ */

let audioCtx = null;
let analyser = null;
let visualizerAnimId = null;

function setupVisualizer(stream) {
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    
    if (!audioCtx) {
      audioCtx = new AudioContextClass();
    } else if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }

    const source = audioCtx.createMediaStreamSource(stream);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 64;
    source.connect(analyser);

    drawVisualizer();
  } catch (err) {
    console.warn('Audio visualizer setup skipped:', err);
  }
}

function drawVisualizer() {
  if (!analyser || !DOM.canvasVisualizer) return;
  
  const ctx = DOM.canvasVisualizer.getContext('2d');
  const width = DOM.canvasVisualizer.width;
  const height = DOM.canvasVisualizer.height;
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  function render() {
    visualizerAnimId = requestAnimationFrame(render);
    analyser.getByteFrequencyData(dataArray);

    ctx.clearRect(0, 0, width, height);

    if (currentState !== State.RECORDING) {
      return;
    }

    const centerX = width / 2;
    const centerY = height / 2;
    const baseRadius = 55;

    // Calculate volume average
    let sum = 0;
    for (let i = 0; i < bufferLength; i++) {
      sum += dataArray[i];
    }
    const avg = sum / bufferLength;
    const waveRadius = baseRadius + (avg * 0.4);

    // Draw glowing pulsing circle around mic
    ctx.beginPath();
    ctx.arc(centerX, centerY, waveRadius, 0, 2 * Math.PI);
    ctx.strokeStyle = `rgba(244, 63, 94, ${Math.min(0.8, avg / 120)})`;
    ctx.lineWidth = 4;
    ctx.shadowBlur = 18;
    ctx.shadowColor = '#f43f5e';
    ctx.stroke();

    // Draw frequency spikes
    const numBars = 24;
    const angleStep = (2 * Math.PI) / numBars;
    
    for (let i = 0; i < numBars; i++) {
      const val = dataArray[i % bufferLength];
      const barLen = Math.max(4, (val / 255) * 28);
      const angle = i * angleStep;

      const x1 = centerX + Math.cos(angle) * (waveRadius + 4);
      const y1 = centerY + Math.sin(angle) * (waveRadius + 4);
      const x2 = centerX + Math.cos(angle) * (waveRadius + 4 + barLen);
      const y2 = centerY + Math.sin(angle) * (waveRadius + 4 + barLen);

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = '#818cf8';
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.stroke();
    }
  }

  render();
}

function stopVisualizer() {
  if (visualizerAnimId) {
    cancelAnimationFrame(visualizerAnimId);
    visualizerAnimId = null;
  }
  if (DOM.canvasVisualizer) {
    const ctx = DOM.canvasVisualizer.getContext('2d');
    ctx.clearRect(0, 0, DOM.canvasVisualizer.width, DOM.canvasVisualizer.height);
  }
}

/* ══════════════════════════════════════════════════════════════
   7. MEDIA RECORDER (MICROPHONE CAPTURE)
══════════════════════════════════════════════════════════════ */

let mediaRecorder = null;
let audioChunks = [];
let mediaStream = null;

function getMimeType() {
  const types = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/ogg',
    'audio/mp4',
  ];
  return types.find(t => MediaRecorder.isTypeSupported(t)) || '';
}

async function startRecording() {
  resetResults();
  
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true
      },
      video: false
    });
  } catch (err) {
    showError(State.STT_ERROR, 'Microphone permission denied. Please allow microphone access in your browser.');
    return;
  }

  setupVisualizer(mediaStream);

  audioChunks = [];
  const mimeType = getMimeType();
  const options = mimeType ? { mimeType } : {};

  try {
    mediaRecorder = new MediaRecorder(mediaStream, options);
  } catch (err) {
    mediaRecorder = new MediaRecorder(mediaStream);
  }

  mediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) audioChunks.push(e.data);
  };

  mediaRecorder.onstop = () => {
    stopStream();
    stopVisualizer();
    const finalType = mediaRecorder.mimeType || 'audio/webm';
    const audioBlob = new Blob(audioChunks, { type: finalType });
    sendVoiceQuery(audioBlob, finalType);
  };

  mediaRecorder.start(250);
  setState(State.RECORDING);
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
}

function stopStream() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop());
    mediaStream = null;
  }
}

/* ══════════════════════════════════════════════════════════════
   8. API CALLS: VOICE & TEXT
══════════════════════════════════════════════════════════════ */

async function sendVoiceQuery(blob, mimeType) {
  const tStart = performance.now();
  setState(State.TRANSCRIBING);
  startStageCycle();

  const formData = new FormData();
  const ext = mimeType.includes('ogg') ? 'ogg' : (mimeType.includes('wav') ? 'wav' : 'webm');
  formData.append('audio', blob, `recording.${ext}`);

  try {
    const res = await fetch(getEndpoint('/api/voice'), {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(30000),
    });

    stopStageCycle();
    const tEnd = performance.now();
    const roundtrip = Math.round(tEnd - tStart);

    if (!res.ok) {
      let errDetail = `Server error (${res.status})`;
      try {
        const body = await res.json();
        if (body.detail) errDetail = body.detail;
      } catch (_) {}
      showError(State.GEN_ERROR, errDetail);
      return;
    }

    const data = await res.json();
    handleRAGResponse(data, roundtrip);
  } catch (err) {
    stopStageCycle();
    showError(State.GEN_ERROR, err.name === 'TimeoutError' ? 'Request timed out.' : 'Network connection error.');
  }
}

async function sendTextQuery(query) {
  if (!query || !query.trim()) return;
  
  resetResults();
  const tStart = performance.now();
  setState(State.RETRIEVING);
  startStageCycle();

  DOM.transcriptText.textContent = query;
  DOM.transcriptCard.style.display = 'block';

  try {
    const res = await fetch(getEndpoint('/api/query'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query.trim(), top_k: CONFIG.topK }),
      signal: AbortSignal.timeout(30000),
    });

    stopStageCycle();
    const tEnd = performance.now();
    const roundtrip = Math.round(tEnd - tStart);

    if (!res.ok) {
      let errDetail = `Server error (${res.status})`;
      try {
        const body = await res.json();
        if (body.detail) errDetail = body.detail;
      } catch (_) {}
      showError(State.GEN_ERROR, errDetail);
      return;
    }

    const data = await res.json();
    handleRAGResponse(data, roundtrip);
  } catch (err) {
    stopStageCycle();
    showError(State.GEN_ERROR, err.name === 'TimeoutError' ? 'Request timed out.' : 'Network error. Ensure backend is running.');
  }
}

/* ══════════════════════════════════════════════════════════════
   9. RESPONSE HANDLER & RESULTS RENDERING
══════════════════════════════════════════════════════════════ */

const REFUSALS = [
  "couldn't find enough information",
  "not enough information",
  "no relevant information",
  "insufficient context",
  "cannot answer",
  "cannot find",
];

function isRefusal(text) {
  if (!text) return false;
  const lower = text.toLowerCase();
  return REFUSALS.some(r => lower.includes(r));
}

function handleRAGResponse(data, frontendRoundtrip) {
  // Transcript
  if (data.transcript) {
    DOM.transcriptText.textContent = data.transcript;
  }

  const answer = data.answer || '';
  const refusal = isRefusal(answer);

  // Answer
  DOM.answerText.textContent = answer;

  // Grounding status badge
  if (refusal) {
    DOM.groundedBadge.className = 'grounded-badge ungrounded';
    DOM.groundedBadge.textContent = '⚠ Insufficient Context';
    DOM.answerCard.style.borderColor = 'var(--color-warning)';
  } else if (data.is_grounded) {
    DOM.groundedBadge.className = 'grounded-badge grounded';
    DOM.groundedBadge.textContent = '✓ Grounded';
    DOM.answerCard.style.borderColor = '';
  } else {
    DOM.groundedBadge.className = 'grounded-badge ungrounded';
    DOM.groundedBadge.textContent = '⚠ Unverified';
    DOM.answerCard.style.borderColor = '';
  }

  // Sources
  const sources = Array.isArray(data.retrieved_sources) ? data.retrieved_sources : [];
  if (sources.length > 0 && !refusal) {
    DOM.sourcesList.innerHTML = sources.map((src, i) => `
      <div class="source-chip">
        <div class="source-index">${i + 1}</div>
        <div class="source-info">
          <div class="source-doc-id" title="${escapeHtml(src.doc_id)}">${escapeHtml(src.doc_id || `Doc #${i + 1}`)}</div>
          <div class="source-strategy">Strategy: ${escapeHtml(src.chunk_strategy || 'Semantic')}</div>
        </div>
        <div class="source-score">${formatScore(src.similarity_score)}</div>
      </div>
    `).join('');
    DOM.sourcesSection.style.display = 'block';
  } else {
    DOM.sourcesSection.style.display = 'none';
  }

  // Latency Breakdown
  renderLatency(data.latency_breakdown || {}, frontendRoundtrip);

  setState(refusal ? State.NO_CONTEXT : State.ANSWER);
}

function renderLatency(lb, frontendRoundtrip) {
  const stages = [
    { label: 'STT (Sarvam)',     key: 'stt' },
    { label: 'Query Embedding',  key: 'embedding' },
    { label: 'FAISS Retrieval',  key: 'retrieval' },
    { label: 'Groq Generation',  key: 'generation' },
    { label: 'Grounding Check',  key: 'grounding' },
  ].filter(s => lb[s.key] !== undefined);

  const totalMs = lb.total ?? null;
  const underTarget = totalMs !== null && totalMs < CONFIG.latencyTargetMs;

  const rows = stages.map(s => `
    <div class="latency-row-label">${escapeHtml(s.label)}</div>
    <div class="latency-row-val">${formatMs(lb[s.key])}</div>
  `).join('');

  const divider = stages.length > 0 ? `<div class="latency-divider"></div>` : '';

  const totalRow = totalMs !== null ? `
    <div class="latency-row-label latency-total-label">Server End-to-End</div>
    <div class="latency-row-val latency-total-val ${underTarget ? 'under-target' : 'over-target'}">${formatMs(totalMs)}</div>
  ` : '';

  const banner = totalMs !== null ? `
    <div class="latency-badge-banner ${underTarget ? 'ok' : 'warning'}">
      ${underTarget ? `✓ Under ${CONFIG.latencyTargetMs} ms target (${formatMs(totalMs)})` : `⚠ Above ${CONFIG.latencyTargetMs} ms target (${formatMs(totalMs)})`}
    </div>
  ` : '';

  const roundtripRow = `
    <div class="latency-row-label" style="font-size:0.76rem;color:var(--color-text-faint)">Client Roundtrip (incl. network)</div>
    <div class="latency-row-val" style="font-size:0.76rem;color:var(--color-text-faint)">${formatMs(frontendRoundtrip)}</div>
  `;

  DOM.latencyGrid.innerHTML = rows + divider + totalRow + banner + roundtripRow;
  DOM.latencySection.style.display = 'block';
}

function showError(state, msg) {
  DOM.resultsWrapper.style.display = 'flex';
  DOM.errorText.textContent = msg;
  DOM.errorCard.style.display = 'block';
  DOM.answerCard.style.display = 'none';
  DOM.sourcesSection.style.display = 'none';
  DOM.latencySection.style.display = 'none';
  setState(state);
}

function resetResults() {
  DOM.errorCard.style.display = 'none';
  DOM.answerCard.style.display = 'block';
  DOM.answerCard.style.borderColor = '';
  DOM.groundedBadge.className = 'grounded-badge';
  DOM.sourcesSection.style.display = 'none';
  DOM.latencySection.style.display = 'none';
  DOM.resultsWrapper.style.display = 'none';
}

/* ══════════════════════════════════════════════════════════════
   10. TEXT-TO-SPEECH & COPY CLIPBOARD
══════════════════════════════════════════════════════════════ */

function speakAnswer() {
  const text = DOM.answerText.textContent;
  if (!text || !('speechSynthesis' in window)) return;

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.05;
  utterance.pitch = 1.0;

  DOM.btnSpeakAnswer.classList.add('active');
  utterance.onend = () => DOM.btnSpeakAnswer.classList.remove('active');
  utterance.onerror = () => DOM.btnSpeakAnswer.classList.remove('active');

  window.speechSynthesis.speak(utterance);
}

async function copyAnswer() {
  const text = DOM.answerText.textContent;
  if (!text) return;

  try {
    await navigator.clipboard.writeText(text);
    const original = DOM.btnCopyAnswer.innerHTML;
    DOM.btnCopyAnswer.innerHTML = `
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="var(--color-success)" stroke-width="2">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      <span>Copied!</span>
    `;
    setTimeout(() => {
      DOM.btnCopyAnswer.innerHTML = original;
    }, 2000);
  } catch (err) {
    console.warn('Clipboard write failed:', err);
  }
}

/* ══════════════════════════════════════════════════════════════
   11. PWA INSTALL PROMPT
══════════════════════════════════════════════════════════════ */

let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  DOM.btnInstall.style.display = 'inline-flex';
});

DOM.btnInstall.addEventListener('click', async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  if (outcome === 'accepted') {
    DOM.btnInstall.style.display = 'none';
  }
  deferredPrompt = null;
});

window.addEventListener('appinstalled', () => {
  DOM.btnInstall.style.display = 'none';
  deferredPrompt = null;
});

/* ══════════════════════════════════════════════════════════════
   12. HEALTH CHECK
══════════════════════════════════════════════════════════════ */

async function checkHealth() {
  try {
    const res = await fetch(getEndpoint('/health'), { signal: AbortSignal.timeout(4000) });
    if (res.ok) {
      DOM.systemStatus.className = 'status-indicator ready';
      DOM.systemStatusText.textContent = 'System Ready';
      DOM.btnMic.disabled = false;
    } else {
      DOM.systemStatus.className = 'status-indicator error';
      DOM.systemStatusText.textContent = 'Backend Error';
    }
  } catch (_) {
    DOM.systemStatus.className = 'status-indicator error';
    DOM.systemStatusText.textContent = 'Backend Offline';
    DOM.btnMic.disabled = false;
  }
}

/* ══════════════════════════════════════════════════════════════
   13. SETTINGS MODAL
══════════════════════════════════════════════════════════════ */

DOM.btnSettings.addEventListener('click', () => {
  DOM.settingApiUrl.value = CONFIG.apiBase;
  DOM.settingTopK.value = CONFIG.topK;
  DOM.topKVal.textContent = CONFIG.topK;
  DOM.settingsModal.style.display = 'flex';
});

DOM.btnCloseSettings.addEventListener('click', () => {
  DOM.settingsModal.style.display = 'none';
});

DOM.settingTopK.addEventListener('input', (e) => {
  DOM.topKVal.textContent = e.target.value;
});

DOM.btnSaveSettings.addEventListener('click', () => {
  CONFIG.apiBase = DOM.settingApiUrl.value.trim();
  CONFIG.topK = parseInt(DOM.settingTopK.value, 10);
  localStorage.setItem('hh_goa_api_base', CONFIG.apiBase);
  localStorage.setItem('hh_goa_top_k', CONFIG.topK);
  DOM.settingsModal.style.display = 'none';
  checkHealth();
});

/* ══════════════════════════════════════════════════════════════
   14. EVENT LISTENERS & INIT
══════════════════════════════════════════════════════════════ */

DOM.btnMic.addEventListener('click', () => {
  if (currentState === State.RECORDING) {
    stopRecording();
  } else {
    startRecording();
  }
});

DOM.textQueryForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const q = DOM.inputTextQuery.value;
  DOM.inputTextQuery.value = '';
  sendTextQuery(q);
});

DOM.suggestionChips.forEach(chip => {
  chip.addEventListener('click', () => {
    const q = chip.dataset.query;
    sendTextQuery(q);
  });
});

DOM.btnSpeakAnswer.addEventListener('click', speakAnswer);
DOM.btnCopyAnswer.addEventListener('click', copyAnswer);

// Helper formatting utilities
function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[m]);
}

function formatMs(val) {
  if (val === null || val === undefined) return '—';
  return `${Math.round(val)} ms`;
}

function formatScore(val) {
  if (val === null || val === undefined) return '—';
  return Number(val).toFixed(3);
}

// Service worker registration
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(err => {
      console.log('SW registration error:', err);
    });
  });
}

// Initial Boot
setState(State.IDLE);
checkHealth();
