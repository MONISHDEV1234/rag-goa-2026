/**
 * app.js — HH Goa 2026 Voice RAG Frontend (Role 2)
 *
 * Responsibilities (Role 2 scope):
 *  - MediaRecorder microphone capture
 *  - Full application state machine
 *  - POST /api/voice to the FastAPI backend
 *  - Latency display from the RAGResponse contract
 *  - Transcript, answer, grounding badge, sources display
 *  - Frontend-side timing instrumentation (click → response)
 *  - Stage-cycling status during the backend HTTP round-trip
 *
 * Backend contract (schemas.py — shared, do NOT modify unilaterally):
 *  RAGResponse {
 *    transcript: string
 *    answer: string
 *    is_grounded: boolean
 *    retrieved_sources: DocumentChunk[]   // {text, doc_id, chunk_strategy, similarity_score}
 *    latency_breakdown: {stt, retrieval, generation, total, ...}
 *  }
 */

'use strict';

/* ══════════════════════════════════════════════════════════════
   CONFIG
══════════════════════════════════════════════════════════════ */

const API_BASE = '';               // same origin — FastAPI serves this page in prod
const VOICE_ENDPOINT = `${API_BASE}/api/voice`;
const HEALTH_ENDPOINT = `${API_BASE}/health`;
const LATENCY_TARGET_MS = 200;    // project target from README.md

/* ══════════════════════════════════════════════════════════════
   STATE MACHINE
   IDLE → RECORDING → PROCESSING → ANSWER | ERROR
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

/**
 * Stage cycling — because /api/voice is a single blocking HTTP call,
 * the frontend cannot know exactly which pipeline stage is running.
 * We cycle through realistic stage messages on a timer so the user
 * sees progress rather than a frozen spinner.
 *
 * Timing is based on the latency budget from README.md:
 *   STT       ~60 ms  → show TRANSCRIBING immediately
 *   Retrieval ~15 ms  → switch after ~70 ms
 *   Generation ~80 ms → switch after ~90 ms
 *   Grounding  ~5 ms  → switch after ~170 ms
 */
const STAGE_CYCLE = [
  { state: State.TRANSCRIBING, delay: 0    },
  { state: State.RETRIEVING,   delay: 900  },
  { state: State.GENERATING,   delay: 1800 },
  { state: State.GROUNDING,    delay: 4000 },
];

let _stageCycleTimers = [];

function startStageCycle() {
  stopStageCycle();
  STAGE_CYCLE.forEach(({ state, delay }) => {
    const t = setTimeout(() => {
      // Only advance if still processing (not if we got a response)
      if ([State.TRANSCRIBING, State.RETRIEVING,
           State.GENERATING,   State.GROUNDING].includes(currentState)) {
        setState(state);
      }
    }, delay);
    _stageCycleTimers.push(t);
  });
}

function stopStageCycle() {
  _stageCycleTimers.forEach(clearTimeout);
  _stageCycleTimers = [];
}

/**
 * Known refusal phrases that the backend returns when context is insufficient.
 * The frontend detects these so it can show the NO_CONTEXT error state
 * instead of displaying a refusal as a normal answer.
 */
const REFUSAL_PHRASES = [
  "couldn't find enough information",
  "i couldn't find",
  "not enough information",
  "no relevant information",
  "insufficient context",
  "cannot answer",
  "cannot find",
];

function isRefusalAnswer(answer) {
  if (!answer) return false;
  const lower = answer.toLowerCase();
  return REFUSAL_PHRASES.some(p => lower.includes(p));
}

/** Transition to a new state and update all UI accordingly. */
function setState(s) {
  currentState = s;
  updateUI(s);
}

/* ══════════════════════════════════════════════════════════════
   DOM REFERENCES
══════════════════════════════════════════════════════════════ */

const elMicBtn        = document.getElementById('btn-mic');
const elMicLabel      = document.getElementById('mic-label');
const elStatusBar     = document.getElementById('status-bar');
const elStatusText    = document.getElementById('status-text');
const elResults       = document.getElementById('results-wrapper');
const elTranscript    = document.getElementById('transcript-text');
const elAnswer        = document.getElementById('answer-text');
const elGroundedBadge = document.getElementById('grounded-badge');
const elErrorCard     = document.getElementById('error-card');
const elErrorText     = document.getElementById('error-text');
const elSourcesSection= document.getElementById('sources-section');
const elSourcesList   = document.getElementById('sources-list');
const elLatencySection= document.getElementById('latency-section');
const elLatencyGrid   = document.getElementById('latency-grid');
const elSystemStatus  = document.getElementById('system-status');
const elSystemStatusText = document.getElementById('system-status-text');

/* ══════════════════════════════════════════════════════════════
   UI UPDATE
══════════════════════════════════════════════════════════════ */

function updateUI(state) {
  const isRecording   = state === State.RECORDING;
  const isProcessing  = [
    State.TRANSCRIBING, State.RETRIEVING, State.GENERATING, State.GROUNDING
  ].includes(state);
  const isDone        = state === State.ANSWER;
  const isError       = [
    State.STT_ERROR, State.RETRIEVAL_ERROR, State.GEN_ERROR,
    State.NO_CONTEXT, State.NO_SPEECH,
  ].includes(state);

  // Mic button
  elMicBtn.disabled    = isProcessing;
  elMicBtn.setAttribute('aria-pressed', isRecording ? 'true' : 'false');
  elMicBtn.setAttribute('aria-label', isRecording ? 'Stop recording' : 'Start recording');
  elMicBtn.classList.toggle('recording', isRecording);

  // Mic label
  const micLabels = {
    [State.IDLE]:      'Click to speak',
    [State.RECORDING]: 'Listening… click to stop',
    [State.ANSWER]:    'Ask another question',
  };
  const errorLabels = 'Click to try again';
  elMicLabel.textContent = isError ? errorLabels
    : (micLabels[state] ?? '');

  // Status bar
  const statusMessages = {
    [State.TRANSCRIBING]: 'Transcribing…',
    [State.RETRIEVING]:   'Searching knowledge base…',
    [State.GENERATING]:   'Generating answer…',
    [State.GROUNDING]:    'Verifying answer…',
  };
  const msg = statusMessages[state];
  if (msg) {
    elStatusText.textContent = msg;
    elStatusBar.classList.add('visible');
  } else {
    elStatusBar.classList.remove('visible');
  }

  // Results wrapper visibility
  if (isDone || isError) {
    elResults.style.display = 'block';
  }

  // Error card
  if (isError) {
    elErrorCard.classList.add('visible');
  } else {
    elErrorCard.classList.remove('visible');
  }
}

/* ══════════════════════════════════════════════════════════════
   HEALTH CHECK
══════════════════════════════════════════════════════════════ */

async function checkHealth() {
  try {
    const res = await fetch(HEALTH_ENDPOINT, { signal: AbortSignal.timeout(5000) });
    if (res.ok) {
      setSystemStatus('ready', 'System Ready');
      elMicBtn.disabled = false;
    } else {
      setSystemStatus('error', 'Backend error');
    }
  } catch {
    // Backend not reachable yet (dev mode)
    setSystemStatus('error', 'Backend offline');
    // Still allow mic — useful when developing the frontend standalone
    elMicBtn.disabled = false;
  }
}

function setSystemStatus(cls, text) {
  elSystemStatus.className = `status-indicator ${cls}`;
  elSystemStatusText.textContent = text;
}

/* ══════════════════════════════════════════════════════════════
   MEDIARECORDER / AUDIO CAPTURE
══════════════════════════════════════════════════════════════ */

let mediaRecorder = null;
let audioChunks   = [];
let recordingStream = null;

/** Determine the best supported MIME type for MediaRecorder. */
function getBestMimeType() {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/ogg',
    'audio/mp4',
  ];
  return candidates.find(t => MediaRecorder.isTypeSupported(t)) ?? '';
}

async function startRecording() {
  try {
    recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  } catch (err) {
    showError(State.STT_ERROR, 'Microphone access denied. Please allow microphone in your browser settings.');
    return;
  }

  audioChunks = [];
  const mimeType = getBestMimeType();
  const options  = mimeType ? { mimeType } : {};

  mediaRecorder = new MediaRecorder(recordingStream, options);

  mediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) audioChunks.push(e.data);
  };

  mediaRecorder.onstop = () => {
    stopStream();
    const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
    processAudio(blob, mediaRecorder.mimeType || 'audio/webm');
  };

  mediaRecorder.start(250);  // collect in 250 ms chunks
  setState(State.RECORDING);
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    setState(State.TRANSCRIBING);  // immediately show next state
  }
}

function stopStream() {
  if (recordingStream) {
    recordingStream.getTracks().forEach(t => t.stop());
    recordingStream = null;
  }
}

/* ══════════════════════════════════════════════════════════════
   PROCESS AUDIO → API
══════════════════════════════════════════════════════════════ */

/** Send audio blob to FastAPI and handle the RAGResponse. */
async function processAudio(blob, mimeType) {
  // Front-end timing: start immediately when blob is ready
  const t_frontend_start = performance.now();

  const formData = new FormData();
  formData.append('audio', blob, `recording.${mimeExtToExt(mimeType)}`);

  // Start stage cycling — shows realistic progress while the HTTP call blocks
  setState(State.TRANSCRIBING);
  startStageCycle();

  let response;
  try {
    response = await fetch(VOICE_ENDPOINT, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(30_000),  // 30 s total timeout
    });
  } catch (err) {
    stopStageCycle();
    if (err.name === 'TimeoutError') {
      showError(State.GEN_ERROR, 'Request timed out. The server took too long to respond.');
    } else {
      showError(State.GEN_ERROR, 'Network error. Please check your connection and try again.');
    }
    return;
  }

  stopStageCycle();

  const t_frontend_end = performance.now();
  const frontendRoundtrip = Math.round(t_frontend_end - t_frontend_start);

  if (!response.ok) {
    let detail = `Server error (${response.status}).`;
    try {
      const body = await response.json();
      if (body.detail) detail = body.detail;
    } catch { /* ignore parse error */ }
    const errState = response.status === 422 ? State.STT_ERROR : State.GEN_ERROR;
    showError(errState, detail);
    return;
  }

  /** @type {RAGResponse} */
  let data;
  try {
    data = await response.json();
  } catch {
    showError(State.GEN_ERROR, 'Could not parse the server response.');
    return;
  }

  // Validate minimal contract fields
  if (typeof data.answer !== 'string' || typeof data.is_grounded !== 'boolean') {
    showError(State.GEN_ERROR, 'Unexpected response format from the server.');
    return;
  }

  // No speech detected
  if (!data.transcript || data.transcript.trim() === '') {
    showError(State.NO_SPEECH, 'No speech detected. Please try speaking clearly.');
    return;
  }

  // Backend refusal (no context / off-topic) — detect from answer text
  if (isRefusalAnswer(data.answer)) {
    // Still display the result card but mark it as NO_CONTEXT
    // so the user sees the refusal message styled appropriately
    displayResult(data, frontendRoundtrip, true);
    return;
  }

  displayResult(data, frontendRoundtrip, false);
}

/* ══════════════════════════════════════════════════════════════
   DISPLAY RESULT
══════════════════════════════════════════════════════════════ */

/**
 * @param {Object}  data              RAGResponse from the backend.
 * @param {number}  frontendRoundtrip Browser-side round-trip in ms.
 * @param {boolean} isRefusal         True if the answer is a backend refusal.
 */
function displayResult(data, frontendRoundtrip, isRefusal = false) {
  // ── Transcript
  elTranscript.textContent = data.transcript;
  elTranscript.classList.add('filled');

  // ── Answer
  elAnswer.textContent = data.answer;
  elAnswer.classList.add('filled');

  // ── Grounded badge
  elGroundedBadge.className = 'grounded-badge ' + (data.is_grounded ? 'grounded' : 'ungrounded');
  elGroundedBadge.textContent = data.is_grounded ? '✓ Grounded' : '⚠ Unverified';

  // ── Refusal styling: override answer card when backend refused
  if (isRefusal) {
    elAnswer.style.color = 'var(--color-warning)';
    elGroundedBadge.className = 'grounded-badge ungrounded';
    elGroundedBadge.textContent = '⚠ Insufficient Context';
  } else {
    elAnswer.style.color = '';
  }

  // ── Sources
  const sources = Array.isArray(data.retrieved_sources) ? data.retrieved_sources : [];
  if (sources.length > 0 && !isRefusal) {
    elSourcesList.innerHTML = sources.map((src, i) => `
      <div class="source-chip">
        <div class="source-index">${i + 1}</div>
        <div class="source-info">
          <div class="source-doc-id" title="${esc(src.doc_id)}">${esc(src.doc_id)}</div>
          <div class="source-strategy">${esc(src.chunk_strategy ?? 'unknown')}</div>
        </div>
        <div class="source-score">${formatScore(src.similarity_score)}</div>
      </div>
    `).join('');
    elSourcesSection.classList.add('visible');
  } else {
    elSourcesSection.classList.remove('visible');
  }

  // ── Latency
  const lb = data.latency_breakdown ?? {};
  renderLatency(lb, frontendRoundtrip);

  setState(isRefusal ? State.NO_CONTEXT : State.ANSWER);
}

function renderLatency(lb, frontendRoundtrip) {
  const rows = [
    { label: 'STT',        key: 'stt' },
    { label: 'Embedding',  key: 'embedding' },
    { label: 'Retrieval',  key: 'retrieval' },
    { label: 'Generation', key: 'generation' },
    { label: 'Grounding',  key: 'grounding' },
  ].filter(r => lb[r.key] !== undefined);

  const totalMs  = lb.total ?? null;
  const underTarget = totalMs !== null && totalMs < LATENCY_TARGET_MS;

  const rowsHtml = rows.map(r => `
    <div class="latency-label">${esc(r.label)}</div>
    <div class="latency-value">${fmtMs(lb[r.key])}</div>
  `).join('');

  const divider = rows.length > 0 ? `<div class="latency-divider"></div>` : '';

  const totalClass = totalMs === null ? ''
    : (underTarget ? 'under-target' : 'over-target');

  const totalRow = totalMs !== null ? `
    <div class="latency-label latency-total-row" style="font-weight:700;color:var(--color-text)">Total</div>
    <div class="latency-value latency-total-row ${totalClass}">${fmtMs(totalMs)}</div>
  ` : '';

  const badge = totalMs !== null ? `
    <div class="latency-target-badge ${underTarget ? 'ok' : 'warning'}">
      ${underTarget ? `✓ Under ${LATENCY_TARGET_MS} ms target` : `⚠ Above ${LATENCY_TARGET_MS} ms target`}
    </div>
  ` : '';

  const frontendRow = `
    <div class="latency-label" style="color:var(--color-text-faint);font-size:0.78rem">Browser round-trip</div>
    <div class="latency-value" style="color:var(--color-text-faint);font-size:0.78rem">${fmtMs(frontendRoundtrip)}</div>
  `;

  elLatencyGrid.innerHTML = rowsHtml + divider + totalRow + badge + frontendRow;
  elLatencySection.classList.add('visible');
}

/* ══════════════════════════════════════════════════════════════
   ERROR / REFUSAL DISPLAY
══════════════════════════════════════════════════════════════ */

const ERROR_MESSAGES = {
  [State.STT_ERROR]:      'Unable to transcribe audio. Please try speaking clearly and try again.',
  [State.RETRIEVAL_ERROR]:'Unable to search the knowledge base. Please try again.',
  [State.GEN_ERROR]:      'The answer service is temporarily unavailable. Please try again.',
  [State.NO_CONTEXT]:     "I couldn't find enough information in the knowledge base to answer that question.",
  [State.NO_SPEECH]:      'No speech detected. Please try speaking clearly.',
};

function showError(errorState, customMsg) {
  elResults.style.display = 'block';
  elErrorText.textContent = customMsg ?? ERROR_MESSAGES[errorState] ?? 'An unexpected error occurred.';
  // Hide answer/sources/latency when showing error
  elTranscript.classList.remove('filled');
  elGroundedBadge.className = 'grounded-badge';
  elAnswer.classList.remove('filled');
  elSourcesSection.classList.remove('visible');
  elLatencySection.classList.remove('visible');
  setState(errorState);
}

/* ══════════════════════════════════════════════════════════════
   MIC BUTTON EVENT
══════════════════════════════════════════════════════════════ */

elMicBtn.addEventListener('click', () => {
  if (currentState === State.RECORDING) {
    stopRecording();
  } else if (
    currentState === State.IDLE ||
    currentState === State.ANSWER ||
    [State.STT_ERROR, State.RETRIEVAL_ERROR, State.GEN_ERROR,
     State.NO_CONTEXT, State.NO_SPEECH].includes(currentState)
  ) {
    // Reset UI before new recording
    elErrorCard.classList.remove('visible');
    elResults.style.display = 'none';
    elTranscript.textContent = 'Your transcribed question appears here.';
    elAnswer.textContent = 'The grounded answer appears here.';
    elTranscript.classList.remove('filled');
    elAnswer.classList.remove('filled');
    elGroundedBadge.className = 'grounded-badge';
    elSourcesSection.classList.remove('visible');
    elLatencySection.classList.remove('visible');
    startRecording();
  }
});

/* ══════════════════════════════════════════════════════════════
   UTILITIES
══════════════════════════════════════════════════════════════ */

/** Escape HTML to prevent XSS when inserting API data into innerHTML. */
function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function fmtMs(val) {
  if (val === null || val === undefined) return '—';
  return `${Math.round(val)} ms`;
}

function formatScore(score) {
  if (score === null || score === undefined) return '';
  return Number(score).toFixed(3);
}

function mimeExtToExt(mimeType) {
  if (!mimeType) return 'webm';
  if (mimeType.includes('ogg')) return 'ogg';
  if (mimeType.includes('wav')) return 'wav';
  if (mimeType.includes('mp4')) return 'mp4';
  return 'webm';
}

/* ══════════════════════════════════════════════════════════════
   INIT
══════════════════════════════════════════════════════════════ */

(async function init() {
  setState(State.IDLE);
  await checkHealth();
})();
