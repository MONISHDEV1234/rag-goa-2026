/**
 * app.js — HH Goa 2026 Voice RAG Frontend (Complete Standalone PWA)
 *
 * Capabilities:
 *  - PWA Service Worker & Install App prompt
 *  - Web Audio API real-time waveform visualizer on mic button
 *  - MediaRecorder audio capture → POST /api/voice
 *  - Text query → POST /api/query
 *  - Suggestion chips for one-tap queries
 *  - Web Speech API TTS readout on answer
 *  - Copy answer to clipboard
 *  - Settings modal: API URL and Top-K
 *  - Latency breakdown display (< 200 ms target)
 *  - Grounding badge (Grounded / Unverified / Insufficient Context)
 */

'use strict';

/* ══════════════════════════════════════════════════════════════
   1. CONFIG & SETTINGS (persisted in localStorage)
══════════════════════════════════════════════════════════════ */

const CONFIG = {
  // Use same-origin relative URL on Railway/cloud; fall back to localStorage override if set
  apiBase:        localStorage.getItem('sonar_api_base') || '',
  topK:           parseInt(localStorage.getItem('sonar_top_k'), 10) || 3,
  latencyTarget:  200,
};

function getEndpoint(path) {
  return CONFIG.apiBase.replace(/\/+$/, '') + path;
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
   4. DOM REFERENCES
══════════════════════════════════════════════════════════════ */

const DOM = {
  btnMic:           document.getElementById('btn-mic'),
  micLabel:         document.getElementById('mic-label'),
  selectMicDevice:  document.getElementById('select-mic-device'),
  btnToggleMic:     document.getElementById('btn-toggle-mic'),
  btnToggleMicText: document.getElementById('btn-toggle-mic-text'),
  btnToggleMicIcon: document.getElementById('btn-toggle-mic-icon'),
  canvasVisualizer: document.getElementById('audio-visualizer'),
  statusBar:        document.getElementById('status-bar'),
  statusText:       document.getElementById('status-text'),
  textQueryForm:    document.getElementById('text-query-form'),
  inputTextQuery:   document.getElementById('input-text-query'),
  btnSubmitText:    document.getElementById('btn-submit-text'),
  suggestionChips:  document.querySelectorAll('.chip'),
  resultsWrapper:   document.getElementById('results-wrapper'),
  errorCard:        document.getElementById('error-card'),
  errorText:        document.getElementById('error-text'),
  transcriptCard:   document.getElementById('transcript-card'),
  transcriptText:   document.getElementById('transcript-text'),
  answerCard:       document.getElementById('answer-card'),
  answerText:       document.getElementById('answer-text'),
  groundedBadge:    document.getElementById('grounded-badge'),
  btnSpeakAnswer:   document.getElementById('btn-speak-answer'),
  btnCopyAnswer:    document.getElementById('btn-copy-answer'),
  sourcesSection:   document.getElementById('sources-section'),
  sourcesList:      document.getElementById('sources-list'),
  latencySection:   document.getElementById('latency-section'),
  latencyGrid:      document.getElementById('latency-grid'),
  systemStatus:     document.getElementById('system-status'),
  systemStatusText: document.getElementById('system-status-text'),
  statusDot:        document.getElementById('status-dot'),
  btnInstall:       document.getElementById('btn-install'),
  btnSettings:      document.getElementById('btn-settings'),
  settingsModal:    document.getElementById('settings-modal'),
  btnCloseSettings: document.getElementById('btn-close-settings'),
  btnSaveSettings:  document.getElementById('btn-save-settings'),
  settingApiUrl:    document.getElementById('setting-api-url'),
  settingTopK:      document.getElementById('setting-top-k'),
  topKVal:          document.getElementById('top-k-val'),

  // For Nerds Cockpit Elements
  btnForNerds:      document.getElementById('btn-for-nerds'),
  nerdsDrawer:      document.getElementById('nerds-hud-drawer'),
  btnCloseNerds:    document.getElementById('btn-close-nerds'),
  nerdOrbState:     document.getElementById('nerd-orb-state'),
  nerdTotalTime:    document.getElementById('nerd-total-time'),
  nerdFaissTime:    document.getElementById('nerd-faiss-time'),
  nerdGroqTime:     document.getElementById('nerd-groq-time'),
  nerdAsrTime:      document.getElementById('nerd-asr-time'),
  pipeNodes: {
    vad:   document.getElementById('pipe-vad'),
    stt:   document.getElementById('pipe-stt'),
    embed: document.getElementById('pipe-embed'),
    faiss: document.getElementById('pipe-faiss'),
    groq:  document.getElementById('pipe-groq'),
    guard: document.getElementById('pipe-guard'),
  },
};

/* ══════════════════════════════════════════════════════════════
   5. UI STATE UPDATER & ORB VISUAL BRIDGE
══════════════════════════════════════════════════════════════ */

function setState(s) {
  currentState = s;

  const isRecording  = s === State.RECORDING;
  const isProcessing = [State.TRANSCRIBING, State.RETRIEVING, State.GENERATING, State.GROUNDING].includes(s);
  const isDone       = s === State.ANSWER || s === State.NO_CONTEXT;
  const isError      = [State.STT_ERROR, State.RETRIEVAL_ERROR, State.GEN_ERROR, State.NO_SPEECH].includes(s);

  // Sync with 3D Orb Multi-State Engine (Feature 5)
  if (window.orbSetState) {
    if (isRecording) {
      window.orbSetState('RECORDING');
    } else if (isProcessing) {
      window.orbSetState('PROCESSING');
    } else {
      window.orbSetState('IDLE');
    }
  }

  // Update Nerd Telemetry State Monitor (Feature 2)
  if (DOM.nerdOrbState) {
    if (isRecording) {
      DOM.nerdOrbState.textContent = 'RECORDING (AURA 3X)';
      DOM.nerdOrbState.className = 'spec-v font-mono text-orange';
    } else if (isProcessing) {
      DOM.nerdOrbState.textContent = `SYNTHESIZING // ${s}`;
      DOM.nerdOrbState.className = 'spec-v font-mono text-cyan';
    } else if (isDone) {
      DOM.nerdOrbState.textContent = 'RESOLVED // READY';
      DOM.nerdOrbState.className = 'spec-v font-mono text-green';
    } else {
      DOM.nerdOrbState.textContent = 'IDLE (MORPH 1.0)';
      DOM.nerdOrbState.className = 'spec-v font-mono text-gold';
    }
  }

  // Update Pipeline Flow Highlight
  if (DOM.pipeNodes) {
    Object.values(DOM.pipeNodes).forEach(n => n?.classList.remove('active'));
    if (s === State.RECORDING) DOM.pipeNodes.vad?.classList.add('active');
    else if (s === State.TRANSCRIBING) DOM.pipeNodes.stt?.classList.add('active');
    else if (s === State.RETRIEVING) {
      DOM.pipeNodes.embed?.classList.add('active');
      DOM.pipeNodes.faiss?.classList.add('active');
    } else if (s === State.GENERATING) DOM.pipeNodes.groq?.classList.add('active');
    else if (s === State.GROUNDING) DOM.pipeNodes.guard?.classList.add('active');
    else if (isDone) DOM.pipeNodes.guard?.classList.add('active');
  }

  // Mic canvas orb state
  if (isProcessing) {
    DOM.btnMic.setAttribute('aria-disabled', 'true');
    DOM.btnMic.style.pointerEvents = 'none';
  } else {
    DOM.btnMic.removeAttribute('aria-disabled');
    DOM.btnMic.style.pointerEvents = '';
  }
  DOM.btnMic.classList.toggle('recording', isRecording);
  DOM.btnMic.setAttribute('aria-pressed', isRecording ? 'true' : 'false');
  DOM.btnMic.setAttribute('aria-label', isRecording ? 'Stop recording' : 'Start voice recording');

  // Mic label & Toggle Button — Dynamic interactive guidance
  if (DOM.btnToggleMic) {
    if (isRecording) {
      DOM.btnToggleMic.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
      DOM.btnToggleMic.style.color = '#fff';
      if (DOM.btnToggleMicText) DOM.btnToggleMicText.textContent = 'STOP & SEND';
      if (DOM.btnToggleMicIcon) DOM.btnToggleMicIcon.textContent = '⏹';
    } else {
      DOM.btnToggleMic.style.background = 'linear-gradient(135deg, #eab308, #ca8a04)';
      DOM.btnToggleMic.style.color = '#000';
      if (DOM.btnToggleMicText) DOM.btnToggleMicText.textContent = 'START RECORDING';
      if (DOM.btnToggleMicIcon) DOM.btnToggleMicIcon.textContent = '🎙';
    }
  }

  if (isError) {
    DOM.micLabel.innerHTML = '<span style="color:#ef4444">⚠ ERROR — CLICK ORB TO RETRY</span>';
  } else if (isRecording) {
    DOM.micLabel.innerHTML = '<span style="color:#f97316; font-weight:700;">● LISTENING… CLICK ORB TO FINISH & SEND</span>';
  } else if (isProcessing) {
    DOM.micLabel.innerHTML = '<span style="color:#06b6d4">⚡ TRANSCRIBING & SEARCHING…</span>';
  } else if (isDone) {
    DOM.micLabel.innerHTML = '<span style="color:#10b981">✓ CLICK ORB TO ASK ANOTHER QUESTION</span>';
  } else {
    DOM.micLabel.innerHTML = '<span>CLICK ORB TO START VOICE QUERY</span>';
  }

  // Status ticker
  const statusMessages = {
    [State.TRANSCRIBING]: 'STT // SARVAM AI TRANSCRIBING…',
    [State.RETRIEVING]:   'FAISS // SEARCHING MSMARCO-XI INDEX…',
    [State.GENERATING]:   'LLM // GROQ GENERATING RESPONSE…',
    [State.GROUNDING]:    'GUARD // GROUNDING VERIFICATION…',
  };
  const msg = statusMessages[s];
  if (msg) {
    DOM.statusText.textContent = msg;
    DOM.statusBar.classList.add('visible');
  } else {
    DOM.statusBar.classList.remove('visible');
  }

  // Error card
  DOM.errorCard.style.display = isError ? 'block' : 'none';

  // Results wrapper
  if (isDone || isError) {
    DOM.resultsWrapper.style.display = 'flex';
  }
}

/* ══════════════════════════════════════════════════════════════
   6. REAL-TIME AUDIO VISUALIZER (Web Audio API)
══════════════════════════════════════════════════════════════ */

let audioCtx = null;
let analyser = null;
let visualizerAnimId = null;

function setupVisualizer(stream) {
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    if (!audioCtx) { audioCtx = new AC(); window._orbAudioCtx = audioCtx; }
    else if (audioCtx.state === 'suspended') audioCtx.resume();

    const source = audioCtx.createMediaStreamSource(stream);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    source.connect(analyser);

    // Expose to orb.js
    window.sonarAnalyser  = analyser;
    window.sonarDataArray = dataArray;
    if (window.orbSetAnalyser) window.orbSetAnalyser(analyser, dataArray);
  } catch (e) { /* optional enhancement */ }
}

function drawVisualizer() {
  if (!analyser || !DOM.canvasVisualizer) return;
  const ctx = DOM.canvasVisualizer.getContext('2d');
  const W = DOM.canvasVisualizer.width;
  const H = DOM.canvasVisualizer.height;
  const buf = new Uint8Array(analyser.frequencyBinCount);

  function frame() {
    visualizerAnimId = requestAnimationFrame(frame);
    analyser.getByteFrequencyData(buf);
    ctx.clearRect(0, 0, W, H);
    if (currentState !== State.RECORDING) return;

    const cx = W / 2, cy = H / 2;
    const avg = buf.reduce((s, v) => s + v, 0) / buf.length;
    const baseR = 52;
    const waveR = baseR + avg * 0.38;

    ctx.beginPath();
    ctx.arc(cx, cy, waveR, 0, 2 * Math.PI);
    ctx.strokeStyle = `rgba(244, 63, 94, ${Math.min(0.85, avg / 110)})`;
    ctx.lineWidth = 4;
    ctx.shadowBlur = 20;
    ctx.shadowColor = '#f43f5e';
    ctx.stroke();
    ctx.shadowBlur = 0;

    const bars = 24;
    for (let i = 0; i < bars; i++) {
      const v = buf[i % buf.length];
      const len = Math.max(3, (v / 255) * 26);
      const angle = (i / bars) * 2 * Math.PI;
      const x1 = cx + Math.cos(angle) * (waveR + 4);
      const y1 = cy + Math.sin(angle) * (waveR + 4);
      const x2 = cx + Math.cos(angle) * (waveR + 4 + len);
      const y2 = cy + Math.sin(angle) * (waveR + 4 + len);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = '#818cf8';
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.stroke();
    }
  }
  frame();
}

function stopVisualizer() {
  if (visualizerAnimId) cancelAnimationFrame(visualizerAnimId);
  visualizerAnimId = null;
  // Clear analyser ref in orb
  window.sonarAnalyser  = null;
  window.sonarDataArray = null;
  if (window.orbSetAnalyser) window.orbSetAnalyser(null, null);
}

/* ══════════════════════════════════════════════════════════════
   7. AUDIO RECORDER — AudioWorklet PCM Capture (bypass MediaRecorder)
   MediaRecorder produces near-empty blobs on many Windows+Chrome
   configs due to codec/driver issues. Instead we capture raw PCM
   samples via AudioWorklet, then encode to WAV in JS.
══════════════════════════════════════════════════════════════ */

let mediaStream       = null;
let isStartingMic     = false;
let recordingTimerInterval = null;
let recordingSeconds  = 0;

// PCM capture state
let pcmAudioCtx       = null;
let pcmWorkletNode    = null;
let pcmSamples        = [];   // Float32Array slices
let pcmSampleRate     = 16000;

// ── WAV encoder ──────────────────────────────────────────────────────────────
function encodeWAV(samples, sampleRate) {
  const numSamples  = samples.length;
  const byteLen     = 44 + numSamples * 2;
  const buffer      = new ArrayBuffer(byteLen);
  const view        = new DataView(buffer);

  function str(offset, s) { for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i)); }
  function u16(offset, v) { view.setUint16(offset, v, true); }
  function u32(offset, v) { view.setUint32(offset, v, true); }

  str(0, 'RIFF');
  u32(4, byteLen - 8);
  str(8, 'WAVE');
  str(12, 'fmt ');
  u32(16, 16);          // subchunk1 size
  u16(20, 1);           // PCM
  u16(22, 1);           // mono
  u32(24, sampleRate);
  u32(28, sampleRate * 2);
  u16(32, 2);           // block align
  u16(34, 16);          // bits per sample
  str(36, 'data');
  u32(40, numSamples * 2);

  let off = 44;
  for (let i = 0; i < numSamples; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(off, s < 0 ? s * 32768 : s * 32767, true);
    off += 2;
  }
  return new Blob([buffer], { type: 'audio/wav' });
}

// ── AudioWorklet inline processor ────────────────────────────────────────────
const WORKLET_CODE = `
class PCMRecorder extends AudioWorkletProcessor {
  constructor() { super(); this._buf = []; }
  process(inputs) {
    const ch = inputs[0]?.[0];
    if (ch) this.port.postMessage(ch.slice());
    return true;
  }
}
registerProcessor('pcm-recorder', PCMRecorder);
`;

let speechRecognizer = null;
let speechTranscript = '';

function setupSpeechRecognition() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) return null;
  try {
    const sr = new SpeechRec();
    sr.continuous = true;
    sr.interimResults = true;
    sr.lang = 'en-IN';
    sr.onresult = (e) => {
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) {
          speechTranscript += e.results[i][0].transcript + ' ';
        } else {
          interim += e.results[i][0].transcript;
        }
      }
      const full = (speechTranscript + ' ' + interim).trim();
      if (full && DOM.micLabel && currentState === State.RECORDING) {
        DOM.micLabel.innerHTML = `<span style="color:#38bdf8; font-weight:800; font-size:0.95rem;">🗣 "${esc(full)}"</span>`;
      }
    };
    sr.onerror = (e) => console.log('[SpeechRecognition]', e.error);
    return sr;
  } catch (_) { return null; }
}

async function populateMicrophones() {
  if (!navigator.mediaDevices?.enumerateDevices) return;
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const mics = devices.filter(d => d.kind === 'audioinput');
    if (!DOM.selectMicDevice) return;
    DOM.selectMicDevice.innerHTML = '';

    if (!mics.length) {
      DOM.selectMicDevice.innerHTML = '<option value="">🎙 Default Microphone</option>';
      return;
    }

    const savedId = localStorage.getItem('sonar_mic_device');
    mics.forEach((d, i) => {
      const opt = document.createElement('option');
      opt.value = d.deviceId;
      opt.textContent = `🎙 ${d.label || `Microphone ${i + 1}`}`;
      if (savedId === d.deviceId) {
        opt.selected = true;
      }
      DOM.selectMicDevice.appendChild(opt);
    });

    DOM.selectMicDevice.onchange = (e) => {
      localStorage.setItem('sonar_mic_device', e.target.value);
      console.log('[Mic Device Selected]:', e.target.value);
    };
  } catch (err) {
    console.warn('[Microphones]', err);
  }
}

async function startRecording() {
  if (isStartingMic || currentState === State.RECORDING) return;
  isStartingMic = true;
  resetResults();
  pcmSamples = [];

  const selectedDeviceId = DOM.selectMicDevice?.value || localStorage.getItem('sonar_mic_device') || '';
  const audioConstraints = selectedDeviceId
    ? { deviceId: { exact: selectedDeviceId }, echoCancellation: true, noiseSuppression: true }
    : { echoCancellation: true, noiseSuppression: true };

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: audioConstraints,
      video: false,
    });
    populateMicrophones();
  } catch (err) {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: false,
      });
      populateMicrophones();
    } catch (_) {
      isStartingMic = false;
      showError(State.STT_ERROR, '❌ Microphone access denied. Allow mic in browser settings and try again.');
      return;
    }
  }

  isStartingMic = false;
  setupVisualizer(mediaStream);

  // Start live browser speech recognition in parallel
  speechTranscript = '';
  try {
    speechRecognizer = setupSpeechRecognition();
    speechRecognizer?.start();
  } catch (_) {}

  // Build AudioContext at mic's native rate (Chrome usually 48000)
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) { showError(State.STT_ERROR, 'Web Audio API not supported.'); return; }
  pcmAudioCtx = new AC();
  pcmSampleRate = pcmAudioCtx.sampleRate;

  // Load worklet as a blob URL
  const blob = new Blob([WORKLET_CODE], { type: 'application/javascript' });
  const blobURL = URL.createObjectURL(blob);
  try {
    await pcmAudioCtx.audioWorklet.addModule(blobURL);
  } catch (e) {
    console.warn('[Worklet] addModule failed:', e.message, '— falling back to ScriptProcessor');
    return startRecordingFallback(mediaStream, pcmAudioCtx);
  }
  URL.revokeObjectURL(blobURL);

  const source = pcmAudioCtx.createMediaStreamSource(mediaStream);
  pcmWorkletNode = new AudioWorkletNode(pcmAudioCtx, 'pcm-recorder');
  pcmWorkletNode.port.onmessage = (e) => {
    if (e.data) pcmSamples.push(...e.data);
  };
  source.connect(pcmWorkletNode);
  pcmWorkletNode.connect(pcmAudioCtx.destination); // needed on some browsers

  setState(State.RECORDING);
  startTimer();
}

// ── ScriptProcessor fallback (Safari / older Chromium) ───────────────────────
function startRecordingFallback(stream, ctx) {
  const source = ctx.createMediaStreamSource(stream);
  const processor = ctx.createScriptProcessor(4096, 1, 1);
  processor.onaudioprocess = (e) => {
    const buf = e.inputBuffer.getChannelData(0);
    pcmSamples.push(...buf);
  };
  source.connect(processor);
  processor.connect(ctx.destination);
  pcmWorkletNode = processor; // reuse stop handle

  setState(State.RECORDING);
  startTimer();
}

function startTimer() {
  recordingSeconds = 0;
  clearInterval(recordingTimerInterval);
  recordingTimerInterval = setInterval(() => {
    recordingSeconds++;
    const mins = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
    const secs = String(recordingSeconds % 60).padStart(2, '0');
    const samples = pcmSamples.length;
    if (DOM.micLabel && currentState === State.RECORDING && !speechTranscript.trim()) {
      DOM.micLabel.innerHTML =
        `<span style="color:#f97316;font-weight:800;font-size:0.95rem;">` +
        `● LISTENING [${mins}:${secs}] &nbsp;|&nbsp; ${Math.round(samples/1000)}k samples` +
        ` — CLICK TO SEND</span>`;
    }
  }, 1000);
}

function stopRecording() {
  clearInterval(recordingTimerInterval);
  try { speechRecognizer?.stop(); } catch (_) {}

  // Stop worklet / processor
  try {
    if (pcmWorkletNode) {
      if (pcmWorkletNode.disconnect) pcmWorkletNode.disconnect();
      pcmWorkletNode = null;
    }
  } catch (_) {}

  stopStream();
  stopVisualizer();

  try { pcmAudioCtx?.close(); } catch (_) {}
  pcmAudioCtx = null;

  const liveText = speechTranscript.trim();
  if (liveText) {
    console.log(`[Browser ASR Recognized]: "${liveText}"`);
    sendTextQuery(liveText);
    return;
  }

  const allSamples = new Float32Array(pcmSamples);
  console.log(`[PCM] Captured ${allSamples.length} samples @ ${pcmSampleRate} Hz = ${(allSamples.length / pcmSampleRate).toFixed(2)}s`);

  if (allSamples.length < pcmSampleRate * 0.3) {
    // Less than 300ms of audio
    showError(State.NO_SPEECH, 'No sound detected from microphone. <strong>Please try toggling between different input devices in the dropdown above</strong> (e.g. Earphones vs Default Microphone).');
    return;
  }

  const wavBlob = encodeWAV(allSamples, pcmSampleRate);
  console.log(`[WAV] Encoded blob: ${wavBlob.size} bytes`);
  processAudio(wavBlob, 'audio/wav');
}

function stopStream() {
  mediaStream?.getTracks().forEach(t => t.stop());
  mediaStream = null;
}

/* ══════════════════════════════════════════════════════════════
  8. AUDIO PROCESSING — REAL BACKEND API
══════════════════════════════════════════════════════════════ */

async function processAudio(blob, mimeType) {
  const tStart = performance.now();
  setState(State.TRANSCRIBING);

  try {
    const audioB64 = await blobToBase64(blob);
    const res = await fetch(getEndpoint('/api/voice'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        audio_b64: audioB64,
        content_type: mimeType || 'audio/webm',
        top_k: CONFIG.topK,
      }),
      signal: AbortSignal.timeout(30_000),
    });
    const tEnd = performance.now();

    if (!res.ok) {
      let detail = `Server error (${res.status})`;
      try { const b = await res.json(); if (b.detail) detail = b.detail; } catch (_) {}
      showError(res.status === 422 ? State.STT_ERROR : State.GEN_ERROR, detail);
      return;
    }

    const data = await res.json();
    handleRAGResponse(data, Math.round(tEnd - tStart));
  } catch (err) {
    showError(State.GEN_ERROR,
      err.name === 'TimeoutError'
        ? 'Request timed out. Try again.'
        : 'Backend not connected. Start the FastAPI server and try again.'
    );
  }
}

async function blobToBase64(blob) {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  let binary = '';
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return btoa(binary);
}

async function sendTextQuery(query) {
  if (!query?.trim()) return;
  resetResults();

  DOM.transcriptText.textContent = query;
  DOM.transcriptCard.style.display = 'block';

  const tStart = performance.now();
  setState(State.RETRIEVING);

  try {
    const res = await fetch(getEndpoint('/api/query'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query.trim(), top_k: CONFIG.topK }),
      signal: AbortSignal.timeout(30_000),
    });
    const tEnd = performance.now();

    if (!res.ok) {
      let detail = `Server error (${res.status})`;
      try { const b = await res.json(); if (b.detail) detail = b.detail; } catch (_) {}
      showError(State.GEN_ERROR, detail);
      return;
    }

    const data = await res.json();
    handleRAGResponse(data, Math.round(tEnd - tStart));
  } catch (err) {
    showError(State.GEN_ERROR,
      err.name === 'TimeoutError'
        ? 'Request timed out.'
        : 'Backend not connected. Start the FastAPI server and try again.'
    );
  }
}

/* ══════════════════════════════════════════════════════════════
   9. RESPONSE HANDLER & RENDERING
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
  const l = text.toLowerCase();
  return REFUSALS.some(r => l.includes(r));
}

function handleRAGResponse(data, frontendRoundtrip) {
  if (data.transcript && data.transcript.trim()) {
    DOM.transcriptText.textContent = data.transcript;
    DOM.transcriptCard.style.display = 'block';
  } else {
    DOM.transcriptCard.style.display = 'none';
  }

  // Handle empty audio refusal specifically
  if (data.refusal && data.refusal_reason === 'empty_query') {
    showError(State.NO_SPEECH, 'No speech detected. <strong>Please try toggling between different input devices in the dropdown above</strong> (e.g. Earphones vs Default Microphone).');
    return;
  }

  const answer  = data.answer || '';
  const refusal = data.refusal === true || isRefusal(answer);

  DOM.answerText.textContent = answer;
  DOM.answerCard.style.display = 'block';

  // Grounding badge
  if (refusal) {
    DOM.groundedBadge.className = 'grounded-badge ungrounded';
    DOM.groundedBadge.textContent = '⚠ Insufficient Context';
    DOM.answerCard.style.borderColor = 'rgba(245, 158, 11, 0.4)';
  } else if (data.is_grounded) {
    DOM.groundedBadge.className = 'grounded-badge grounded';
    DOM.groundedBadge.textContent = '✓ Grounded';
    DOM.answerCard.style.borderColor = '';
  } else {
    DOM.groundedBadge.className = 'grounded-badge ungrounded';
    DOM.groundedBadge.textContent = '⚠ Unverified';
    DOM.answerCard.style.borderColor = '';
  }

  // Update Nerd Telemetry Metrics (Feature 2)
  if (DOM.nerdTotalTime) DOM.nerdTotalTime.textContent = `${frontendRoundtrip} ms`;
  if (data.latency_breakdown) {
    if (DOM.nerdFaissTime && data.latency_breakdown.retrieval !== undefined) {
      DOM.nerdFaissTime.textContent = `${data.latency_breakdown.retrieval} ms`;
    }
    if (DOM.nerdGroqTime && data.latency_breakdown.generation !== undefined) {
      DOM.nerdGroqTime.textContent = `${data.latency_breakdown.generation} ms`;
    }
    if (DOM.nerdAsrTime && data.latency_breakdown.stt !== undefined) {
      DOM.nerdAsrTime.textContent = `${data.latency_breakdown.stt} ms`;
    }
  }

  // Sources
  const sources = Array.isArray(data.retrieved_sources) ? data.retrieved_sources : [];
  if (sources.length > 0 && !refusal) {
    DOM.sourcesList.innerHTML = sources.map((src, i) => `
      <div class="source-chip">
        <div class="source-index">${i + 1}</div>
        <div class="source-info">
          <div class="source-doc-id" title="${esc(src.doc_id)}">${esc(src.doc_id || `Doc #${i + 1}`)}</div>
          <div class="source-strategy">${esc(src.chunk_strategy || 'semantic')}</div>
        </div>
        <div class="source-score">${fmt(src.similarity_score)}</div>
      </div>
    `).join('');
    DOM.sourcesSection.style.display = 'block';
  } else {
    DOM.sourcesSection.style.display = 'none';
  }

  // Latency breakdown
  renderLatency(data.latency_breakdown || {}, frontendRoundtrip);

  setState(refusal ? State.NO_CONTEXT : State.ANSWER);

  // Smoothly scroll results into view
  setTimeout(() => {
    DOM.resultsWrapper?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 100);
}

function renderLatency(lb, frontendRoundtrip) {
  const stages = [
    { label: 'STT (Sarvam AI)',   key: 'stt' },
    { label: 'Query Embedding',   key: 'embedding' },
    { label: 'FAISS Retrieval',   key: 'retrieval' },
    { label: 'Grounding Check',   key: 'grounding' },
    { label: 'Groq Generation',   key: 'generation' },
  ].filter(s => lb[s.key] !== undefined);

  const faissMs     = lb.retrieval ?? lb.total ?? 0;
  const underTarget = faissMs < CONFIG.latencyTarget;

  const rows = stages.map(s => `
    <div class="latency-row-label">${esc(s.label)}</div>
    <div class="latency-row-val">${fmtMs(lb[s.key])}</div>
  `).join('');

  const div = stages.length > 0 ? `<div class="latency-divider"></div>` : '';

  const totalRow = `
    <div class="latency-row-label latency-total-label">FAISS Retrieval Time</div>
    <div class="latency-row-val latency-total-val ${underTarget ? 'under-target' : 'over-target'}">${fmtMs(faissMs)}</div>
  `;

  const banner = `
    <div class="latency-badge-banner ${underTarget ? 'ok' : 'warning'}">
      ${underTarget
        ? `✓ Under ${CONFIG.latencyTarget} ms target (${fmtMs(faissMs)})`
        : `⚠ Above ${CONFIG.latencyTarget} ms target (${fmtMs(faissMs)})`}
    </div>
  `;

  const rtRow = `
    <div class="latency-row-label" style="font-size:.76rem;color:var(--color-text-faint)">Full Roundtrip (incl. STT &amp; LLM)</div>
    <div class="latency-row-val"   style="font-size:.76rem;color:var(--color-text-faint)">${fmtMs(frontendRoundtrip)}</div>
  `;

  DOM.latencyGrid.innerHTML = rows + div + totalRow + banner + rtRow;
  DOM.latencySection.style.display = 'block';
}

function showError(state, msg) {
  DOM.resultsWrapper.style.display = 'flex';
  DOM.errorText.innerHTML = msg;
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
  DOM.transcriptText.textContent = '';
}

/* ══════════════════════════════════════════════════════════════
   10. TTS & CLIPBOARD
══════════════════════════════════════════════════════════════ */

function speakAnswer() {
  const text = DOM.answerText.textContent;
  if (!text || !('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.05;
  DOM.btnSpeakAnswer.classList.add('active');

  // Trigger Harmonic Speaking Orb Visual State (Feature 5)
  if (window.orbSetSpeaking) window.orbSetSpeaking(true);

  const cleanup = () => {
    DOM.btnSpeakAnswer.classList.remove('active');
    if (window.orbSetSpeaking) window.orbSetSpeaking(false);
  };

  u.onend   = cleanup;
  u.onerror = cleanup;
  window.speechSynthesis.speak(u);
}

async function copyAnswer() {
  const text = DOM.answerText.textContent;
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    const orig = DOM.btnCopyAnswer.innerHTML;
    DOM.btnCopyAnswer.innerHTML = `
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="var(--color-success)" stroke-width="2.5">
        <polyline points="20 6 9 17 4 12"/>
      </svg><span>Copied!</span>`;
    setTimeout(() => { DOM.btnCopyAnswer.innerHTML = orig; }, 2000);
  } catch (_) {}
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
  if (outcome === 'accepted') DOM.btnInstall.style.display = 'none';
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
  DOM.systemStatus.className = 'sys-status';
  DOM.systemStatusText.textContent = 'CONNECTING…';
  try {
    // Use 8s timeout to handle Railway cold starts
    const res = await fetch(getEndpoint('/health'), { signal: AbortSignal.timeout(8000) });
    const health = res.ok ? await res.json() : null;
    const retrievalReady = !health?.retrieval || health.retrieval.status === 'healthy';
    if (res.ok && retrievalReady) {
      DOM.systemStatus.className = 'sys-status ready';
      DOM.systemStatusText.textContent = 'ONLINE';
      DOM.btnMic.removeAttribute('disabled');
    } else {
      DOM.systemStatus.className = 'sys-status error';
      DOM.systemStatusText.textContent = 'BACKEND ERR';
      enableBrowserMode();
    }
  } catch (err) {
    console.warn('[Health] Backend check failed:', err.message);
    enableBrowserMode();
  }
}

function enableBrowserMode() {
  DOM.btnMic.removeAttribute('disabled');
  DOM.systemStatus.className = 'sys-status error';
  DOM.systemStatusText.textContent = 'BACKEND OFFLINE';
}

/* ══════════════════════════════════════════════════════════════
   13. SETTINGS & FOR NERDS DRAWER
══════════════════════════════════════════════════════════════ */

function toggleNerdsDrawer(forceOpen) {
  if (!DOM.nerdsDrawer || !DOM.btnForNerds) return;
  const isHidden = DOM.nerdsDrawer.style.display === 'none';
  const shouldOpen = typeof forceOpen === 'boolean' ? forceOpen : isHidden;

  DOM.nerdsDrawer.style.display = shouldOpen ? 'block' : 'none';
  DOM.btnForNerds.classList.toggle('active', shouldOpen);
  DOM.btnForNerds.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
  localStorage.setItem('sonar_nerds_open', shouldOpen ? 'true' : 'false');
}

DOM.btnForNerds?.addEventListener('click', () => toggleNerdsDrawer());
DOM.btnCloseNerds?.addEventListener('click', () => toggleNerdsDrawer(false));

DOM.btnSettings.addEventListener('click', () => {
  DOM.settingApiUrl.value  = CONFIG.apiBase;
  DOM.settingTopK.value    = CONFIG.topK;
  DOM.topKVal.textContent  = CONFIG.topK;
  DOM.settingsModal.style.display = 'flex';
});

DOM.btnCloseSettings.addEventListener('click', () => {
  DOM.settingsModal.style.display = 'none';
});

DOM.settingTopK.addEventListener('input', (e) => {
  DOM.topKVal.textContent = e.target.value;
});

DOM.btnSaveSettings.addEventListener('click', () => {
  CONFIG.apiBase  = DOM.settingApiUrl.value.trim();
  CONFIG.topK     = parseInt(DOM.settingTopK.value, 10);
  localStorage.setItem('sonar_api_base', CONFIG.apiBase);
  localStorage.setItem('sonar_top_k',    CONFIG.topK);
  DOM.settingsModal.style.display = 'none';
  checkHealth();
});

/* ══════════════════════════════════════════════════════════════
   14. EVENT WIRING
══════════════════════════════════════════════════════════════ */

function handleMicToggle() {
  if (currentState === State.RECORDING) {
    stopRecording();
  } else if ([State.IDLE, State.ANSWER, State.NO_CONTEXT,
               State.STT_ERROR, State.RETRIEVAL_ERROR,
               State.GEN_ERROR, State.NO_SPEECH].includes(currentState)) {
    startRecording();
  }
}

DOM.btnMic.addEventListener('click', handleMicToggle);
DOM.micLabel?.addEventListener('click', handleMicToggle);
DOM.btnToggleMic?.addEventListener('click', handleMicToggle);

// Auto-discover available microphones on page load
populateMicrophones();

DOM.textQueryForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const q = DOM.inputTextQuery.value.trim();
  DOM.inputTextQuery.value = '';
  if (q) sendTextQuery(q);
});

DOM.suggestionChips.forEach(chip => {
  chip.addEventListener('click', () => sendTextQuery(chip.dataset.query));
});

DOM.btnSpeakAnswer.addEventListener('click', speakAnswer);
DOM.btnCopyAnswer.addEventListener('click', copyAnswer);

// Close modal on backdrop click
DOM.settingsModal.addEventListener('click', (e) => {
  if (e.target === DOM.settingsModal) DOM.settingsModal.style.display = 'none';
});

/* ══════════════════════════════════════════════════════════════
   15. UTILITY FUNCTIONS
══════════════════════════════════════════════════════════════ */

function esc(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

function fmtMs(v) {
  if (v === null || v === undefined) return '—';
  return `${Math.round(v)} ms`;
}

function fmt(v) {
  if (v === null || v === undefined) return '—';
  return Number(v).toFixed(3);
}

/* ══════════════════════════════════════════════════════════════
   16. SERVICE WORKER & INIT
══════════════════════════════════════════════════════════════ */

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}

// Boot
setState(State.IDLE);
checkHealth();

// Restore 'FOR NERDS' drawer state if user previously had it open
if (localStorage.getItem('sonar_nerds_open') === 'true') {
  toggleNerdsDrawer(true);
}

/* ══════════════════════════════════════════════════════════════
   17. NAVBAR — magnetic hover + click ripple
══════════════════════════════════════════════════════════════ */
(function initNavbarMotion() {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const items = document.querySelectorAll('.navbar .nav-mag');

  items.forEach((item) => {
    if (!reduce) {
      item.addEventListener('mousemove', (e) => {
        const rect = item.getBoundingClientRect();
        const dx = (e.clientX - rect.left - rect.width / 2) * 0.28;
        const dy = (e.clientY - rect.top - rect.height / 2) * 0.28;
        item.style.transform = `translate3d(${dx}px, ${dy}px, 0)`;
      });
      item.addEventListener('mouseleave', () => {
        item.style.transform = 'translate3d(0, 0, 0)';
      });
    }

    item.addEventListener('click', (e) => {
      const ripple = document.createElement('span');
      ripple.className = 'nav-ripple';
      const rect = item.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height) * 1.35;
      ripple.style.width = ripple.style.height = `${size}px`;
      ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
      ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
      item.appendChild(ripple);
      ripple.addEventListener('animationend', () => ripple.remove());
    });
  });
})();

