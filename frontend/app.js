/**
 * app.js — HH Goa 2026 Voice RAG Frontend (Complete Standalone PWA)
 *
 * Capabilities:
 *  - PWA Service Worker & Install App prompt
 *  - Web Audio API real-time waveform visualizer on mic button
 *  - MediaRecorder audio capture → POST /api/voice (or Demo Mode)
 *  - Text query fallback → POST /api/query (or Demo Mode)
 *  - Suggestion chips for one-tap queries
 *  - Demo Mode: full pipeline simulation with realistic mock data (no backend needed)
 *  - Web Speech API TTS readout on answer
 *  - Copy answer to clipboard
 *  - Settings modal: API URL, Top-K, Demo Mode toggle
 *  - Latency breakdown display (< 200 ms target)
 *  - Grounding badge (Grounded / Unverified / Insufficient Context)
 */

'use strict';

/* ══════════════════════════════════════════════════════════════
   1. CONFIG & SETTINGS (persisted in localStorage)
══════════════════════════════════════════════════════════════ */

const CONFIG = {
  apiBase:        localStorage.getItem('hh_goa_api_base') || '',
  topK:           parseInt(localStorage.getItem('hh_goa_top_k'), 10) || 3,
  demoMode:       localStorage.getItem('hh_goa_demo') === 'true', // default OFF — uses real skeleton backend
  latencyTarget:  200,
};

function getEndpoint(path) {
  return CONFIG.apiBase.replace(/\/+$/, '') + path;
}

/* ══════════════════════════════════════════════════════════════
   2. DEMO MODE — Realistic Mock Responses
   Used when backend is not yet wired or Demo Mode is enabled.
══════════════════════════════════════════════════════════════ */

const DEMO_QA = [
  {
    keywords: ['retrieval', 'rag', 'augmented'],
    transcript: 'What is retrieval augmented generation?',
    answer: 'Retrieval-Augmented Generation (RAG) is a technique that combines a retrieval system with a generative language model. Instead of relying solely on the model\'s parametric knowledge, RAG first retrieves relevant passages from an external knowledge base (such as MSMARCO-XI using FAISS), then conditions the LLM generation on those retrieved passages. This reduces hallucinations and ensures the answer is grounded in verifiable documents.',
    sources: [
      { doc_id: 'msmarco-xi-doc-00412', chunk_strategy: 'semantic',  similarity_score: 0.921 },
      { doc_id: 'msmarco-xi-doc-01876', chunk_strategy: 'sliding',   similarity_score: 0.887 },
      { doc_id: 'msmarco-xi-doc-03201', chunk_strategy: 'semantic',  similarity_score: 0.812 },
    ],
    latency: { stt: 58, embedding: 9, retrieval: 5, generation: 74, grounding: 4, total: 150 },
    is_grounded: true,
  },
  {
    keywords: ['transformer', 'attention', 'architecture'],
    transcript: 'How does the transformer architecture work?',
    answer: 'The Transformer architecture, introduced in "Attention Is All You Need" (Vaswani et al., 2017), relies entirely on self-attention mechanisms instead of recurrence. Each token attends to every other token in the sequence through multi-head attention, computed as softmax(QKᵀ/√dₖ)V. This allows parallel processing and captures long-range dependencies efficiently. Encoder-decoder variants are used for translation; decoder-only variants (like GPT) for generation.',
    sources: [
      { doc_id: 'msmarco-xi-doc-00891', chunk_strategy: 'semantic',  similarity_score: 0.944 },
      { doc_id: 'msmarco-xi-doc-02114', chunk_strategy: 'semantic',  similarity_score: 0.903 },
    ],
    latency: { stt: 61, embedding: 8, retrieval: 4, generation: 81, grounding: 3, total: 157 },
    is_grounded: true,
  },
  {
    keywords: ['faiss', 'vector', 'search', 'index'],
    transcript: 'How does in-memory vector search with FAISS work?',
    answer: 'FAISS (Facebook AI Similarity Search) is a library for efficient similarity search over dense vectors. In this system, document chunks are embedded offline using FastEmbed (BAAI/bge-small-en-v1.5), and stored in a FAISS IndexFlatIP index loaded entirely into RAM at startup. At query time, the query is embedded (~9 ms) and FAISS performs an exact inner-product search (~5 ms) to return the top-K most similar passages without any disk I/O.',
    sources: [
      { doc_id: 'msmarco-xi-doc-04532', chunk_strategy: 'sliding',   similarity_score: 0.912 },
      { doc_id: 'msmarco-xi-doc-01234', chunk_strategy: 'metadata',  similarity_score: 0.878 },
      { doc_id: 'msmarco-xi-doc-03891', chunk_strategy: 'semantic',  similarity_score: 0.843 },
    ],
    latency: { stt: 54, embedding: 11, retrieval: 6, generation: 68, grounding: 5, total: 144 },
    is_grounded: true,
  },
  {
    keywords: ['chunking', 'semantic', 'sliding', 'window'],
    transcript: 'What is semantic chunking and how does it differ from sliding window?',
    answer: 'Semantic chunking splits documents at natural meaning boundaries — detected by measuring cosine similarity drops between adjacent sentence embeddings. This keeps related ideas together in one chunk. Sliding-window chunking, by contrast, uses fixed-size overlapping windows (e.g. 4 sentences, step 2) regardless of content boundaries. Sliding windows are faster to compute but may split mid-thought. Semantic chunking typically produces better retrieval quality at the cost of slightly more computation during the offline indexing phase.',
    sources: [
      { doc_id: 'msmarco-xi-doc-02977', chunk_strategy: 'semantic',  similarity_score: 0.931 },
      { doc_id: 'msmarco-xi-doc-04102', chunk_strategy: 'sliding',   similarity_score: 0.891 },
    ],
    latency: { stt: 63, embedding: 10, retrieval: 5, generation: 79, grounding: 4, total: 161 },
    is_grounded: true,
  },
  {
    keywords: ['sarvam', 'stt', 'speech', 'transcri'],
    transcript: 'How does the Sarvam AI speech-to-text work?',
    answer: 'Sarvam AI\'s saarika:v2.5 model is a multilingual ASR (Automatic Speech Recognition) system optimized for Indian languages including English with Indian accents. In this pipeline, audio is captured via the browser\'s MediaRecorder API as WebM/Opus, sent via a multipart POST request to the Sarvam API, and the transcript is returned in under 60 ms on average. An async httpx client with connection pooling and tenacity retries handles transient failures without blocking the main event loop.',
    sources: [
      { doc_id: 'msmarco-xi-doc-00147', chunk_strategy: 'semantic',  similarity_score: 0.908 },
      { doc_id: 'msmarco-xi-doc-01763', chunk_strategy: 'sliding',   similarity_score: 0.867 },
    ],
    latency: { stt: 57, embedding: 9, retrieval: 5, generation: 72, grounding: 4, total: 147 },
    is_grounded: true,
  },
  {
    keywords: ['latency', 'performance', '200ms', 'fast'],
    transcript: 'How does the system achieve under 200 ms latency?',
    answer: 'The sub-200 ms target is achieved through: (1) FAISS loaded entirely in RAM at startup — zero disk I/O per request; (2) FastEmbed\'s BGE-small-en-v1.5 model pre-warmed, embedding in ~9 ms; (3) Groq\'s llama-3.1-8b-instant LLM generating in ~70 ms via optimized inference hardware; (4) Single async event loop with httpx connection pooling for both Sarvam and Groq; (5) Prompt limited to ≤512 tokens; (6) Max output tokens capped at 256. The latency budget: STT ~60ms + Embedding ~10ms + FAISS ~5ms + LLM ~75ms + Grounding ~5ms = ~155ms.',
    sources: [
      { doc_id: 'msmarco-xi-doc-03341', chunk_strategy: 'semantic',  similarity_score: 0.956 },
      { doc_id: 'msmarco-xi-doc-04812', chunk_strategy: 'metadata',  similarity_score: 0.902 },
      { doc_id: 'msmarco-xi-doc-02256', chunk_strategy: 'sliding',   similarity_score: 0.871 },
    ],
    latency: { stt: 55, embedding: 8, retrieval: 4, generation: 71, grounding: 4, total: 142 },
    is_grounded: true,
  },
  {
    keywords: ['groq', 'llm', 'llama', 'generation'],
    transcript: 'What LLM does this system use and why Groq?',
    answer: 'This system uses Meta\'s Llama 3.1 8B Instant model, served via Groq\'s LPU (Language Processing Unit) inference hardware. Groq was chosen because its LPU architecture delivers dramatically lower generation latency (~70ms for short answers) compared to GPU-based APIs (~150-300ms). The 8B parameter model strikes the right balance between reasoning quality and speed. Prompts are kept short (≤512 tokens) and output is capped at 256 tokens to minimize generation time while still producing complete, useful answers.',
    sources: [
      { doc_id: 'msmarco-xi-doc-01508', chunk_strategy: 'semantic',  similarity_score: 0.935 },
      { doc_id: 'msmarco-xi-doc-03702', chunk_strategy: 'sliding',   similarity_score: 0.892 },
    ],
    latency: { stt: 60, embedding: 9, retrieval: 5, generation: 69, grounding: 3, total: 146 },
    is_grounded: true,
  },
];

const DEMO_REFUSAL = {
  transcript: '',
  answer: "I couldn't find enough information in the provided knowledge base to answer that question. Please try rephrasing or asking about RAG, transformers, FAISS, chunking strategies, or system architecture.",
  sources: [],
  latency: { stt: 55, embedding: 9, retrieval: 4, generation: 0, grounding: 2, total: 70 },
  is_grounded: false,
};

function getDemoResponse(query) {
  if (!query) return DEMO_REFUSAL;
  const lower = query.toLowerCase();
  const match = DEMO_QA.find(q => q.keywords.some(k => lower.includes(k)));
  if (match) return { ...match, transcript: match.transcript };
  return { ...DEMO_REFUSAL, transcript: query };
}

function addJitter(ms) {
  return Math.round(ms * (0.88 + Math.random() * 0.24));
}

async function runDemoMode(query) {
  // Simulate realistic STT delay
  setState(State.TRANSCRIBING);
  await sleep(addJitter(600));

  // Simulate retrieval
  setState(State.RETRIEVING);
  await sleep(addJitter(400));

  // Simulate generation
  setState(State.GENERATING);
  await sleep(addJitter(800));

  // Simulate grounding check
  setState(State.GROUNDING);
  await sleep(addJitter(250));

  const raw = getDemoResponse(query);
  // Apply jitter to latency numbers for realism
  const latency = {};
  for (const [k, v] of Object.entries(raw.latency)) {
    latency[k] = k === 'total' ? undefined : addJitter(v);
  }
  latency.total = Object.entries(latency)
    .filter(([k]) => k !== 'total')
    .reduce((s, [, v]) => s + (v || 0), 0);

  const frontendRoundtrip = latency.total + addJitter(12);

  handleRAGResponse({
    transcript:         raw.transcript || query,
    answer:             raw.answer,
    is_grounded:        raw.is_grounded,
    retrieved_sources:  raw.sources,
    latency_breakdown:  latency,
  }, frontendRoundtrip);
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

/* ══════════════════════════════════════════════════════════════
   3. STATE MACHINE
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
  demoBadge:        document.getElementById('demo-badge'),
  btnInstall:       document.getElementById('btn-install'),
  btnSettings:      document.getElementById('btn-settings'),
  settingsModal:    document.getElementById('settings-modal'),
  btnCloseSettings: document.getElementById('btn-close-settings'),
  btnSaveSettings:  document.getElementById('btn-save-settings'),
  settingApiUrl:    document.getElementById('setting-api-url'),
  settingTopK:      document.getElementById('setting-top-k'),
  topKVal:          document.getElementById('top-k-val'),
  settingDemoMode:  document.getElementById('setting-demo-mode'),
};

/* ══════════════════════════════════════════════════════════════
   5. UI STATE UPDATER
══════════════════════════════════════════════════════════════ */

function setState(s) {
  currentState = s;

  const isRecording  = s === State.RECORDING;
  const isProcessing = [State.TRANSCRIBING, State.RETRIEVING, State.GENERATING, State.GROUNDING].includes(s);
  const isDone       = s === State.ANSWER || s === State.NO_CONTEXT;
  const isError      = [State.STT_ERROR, State.RETRIEVAL_ERROR, State.GEN_ERROR, State.NO_SPEECH].includes(s);

  // Mic button
  DOM.btnMic.disabled = isProcessing;
  DOM.btnMic.setAttribute('aria-pressed', isRecording ? 'true' : 'false');
  DOM.btnMic.setAttribute('aria-label', isRecording ? 'Stop recording' : 'Start voice recording');
  DOM.btnMic.classList.toggle('recording', isRecording);

  // Mic label
  if (isError) {
    DOM.micLabel.textContent = 'Tap to try again';
  } else if (isRecording) {
    DOM.micLabel.textContent = 'Listening… tap to stop';
  } else if (isDone) {
    DOM.micLabel.textContent = 'Tap to ask another';
  } else {
    DOM.micLabel.textContent = 'Tap to speak';
  }

  // Status bar
  const statusMessages = {
    [State.TRANSCRIBING]: CONFIG.demoMode ? '🎙 Transcribing speech (demo)…'  : 'Transcribing speech…',
    [State.RETRIEVING]:   CONFIG.demoMode ? '🔍 Searching MSMARCO-XI (demo)…' : 'Searching MSMARCO-XI index…',
    [State.GENERATING]:   CONFIG.demoMode ? '🤖 Generating answer (demo)…'    : 'Generating grounded answer…',
    [State.GROUNDING]:    CONFIG.demoMode ? '✅ Verifying citations (demo)…'   : 'Verifying citations & grounding…',
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

function updateDemoUI() {
  if (DOM.demoBadge) {
    DOM.demoBadge.style.display = CONFIG.demoMode ? 'inline-flex' : 'none';
  }
  if (CONFIG.demoMode) {
    DOM.systemStatus.className = 'status-indicator demo';
    DOM.systemStatusText.textContent = 'Demo Mode';
    DOM.btnMic.disabled = false;
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
    if (!audioCtx) audioCtx = new AC();
    else if (audioCtx.state === 'suspended') audioCtx.resume();

    const source = audioCtx.createMediaStreamSource(stream);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 64;
    source.connect(analyser);
    drawVisualizer();
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
  if (DOM.canvasVisualizer) {
    DOM.canvasVisualizer.getContext('2d').clearRect(
      0, 0, DOM.canvasVisualizer.width, DOM.canvasVisualizer.height
    );
  }
}

/* ══════════════════════════════════════════════════════════════
   7. MEDIA RECORDER (MICROPHONE CAPTURE)
══════════════════════════════════════════════════════════════ */

let mediaRecorder = null;
let audioChunks   = [];
let mediaStream   = null;
let lastRecordedBlob = null;
let lastMimeType     = 'audio/webm';

function getMimeType() {
  const types = ['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/ogg','audio/mp4'];
  return types.find(t => MediaRecorder.isTypeSupported(t)) || '';
}

async function startRecording() {
  resetResults();

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true },
      video: false,
    });
  } catch (err) {
    showError(State.STT_ERROR, 'Microphone permission denied. Please allow microphone access.');
    return;
  }

  setupVisualizer(mediaStream);
  audioChunks = [];
  const mime = getMimeType();
  try { mediaRecorder = new MediaRecorder(mediaStream, mime ? { mimeType: mime } : {}); }
  catch (_) { mediaRecorder = new MediaRecorder(mediaStream); }

  mediaRecorder.ondataavailable = (e) => { if (e.data?.size > 0) audioChunks.push(e.data); };

  mediaRecorder.onstop = () => {
    stopStream();
    stopVisualizer();
    lastMimeType = mediaRecorder.mimeType || 'audio/webm';
    lastRecordedBlob = new Blob(audioChunks, { type: lastMimeType });
    processAudio(lastRecordedBlob, lastMimeType);
  };

  mediaRecorder.start(250);
  setState(State.RECORDING);
}

function stopRecording() {
  if (mediaRecorder?.state !== 'inactive') mediaRecorder.stop();
}

function stopStream() {
  mediaStream?.getTracks().forEach(t => t.stop());
  mediaStream = null;
}

/* ══════════════════════════════════════════════════════════════
   8. AUDIO PROCESSING — ROUTES TO DEMO OR REAL API
══════════════════════════════════════════════════════════════ */

async function processAudio(blob, mimeType) {
  if (CONFIG.demoMode) {
    // In demo mode, run the full simulated pipeline
    await runDemoMode('');
    return;
  }

  const tStart = performance.now();
  setState(State.TRANSCRIBING);

  const formData = new FormData();
  const ext = mimeType.includes('ogg') ? 'ogg' : mimeType.includes('wav') ? 'wav' : 'webm';
  formData.append('audio', blob, `recording.${ext}`);

  try {
    const res = await fetch(getEndpoint('/api/voice'), {
      method: 'POST',
      body: formData,
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
        ? 'Request timed out. Try enabling Demo Mode in Settings.'
        : 'Backend not connected. Enable Demo Mode in ⚙ Settings to explore the UI.'
    );
  }
}

async function sendTextQuery(query) {
  if (!query?.trim()) return;
  resetResults();

  DOM.transcriptText.textContent = query;
  DOM.transcriptCard.style.display = 'block';

  if (CONFIG.demoMode) {
    await runDemoMode(query);
    return;
  }

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
        : 'Backend not connected. Enable Demo Mode in ⚙ Settings.'
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
  if (data.transcript) DOM.transcriptText.textContent = data.transcript;

  const answer  = data.answer || '';
  const refusal = isRefusal(answer);

  DOM.answerText.textContent = answer;

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
}

function renderLatency(lb, frontendRoundtrip) {
  const stages = [
    { label: 'STT (Sarvam AI)',   key: 'stt' },
    { label: 'Query Embedding',   key: 'embedding' },
    { label: 'FAISS Retrieval',   key: 'retrieval' },
    { label: 'Groq Generation',   key: 'generation' },
    { label: 'Grounding Check',   key: 'grounding' },
  ].filter(s => lb[s.key] !== undefined);

  const totalMs     = lb.total ?? null;
  const underTarget = totalMs !== null && totalMs < CONFIG.latencyTarget;

  const rows = stages.map(s => `
    <div class="latency-row-label">${esc(s.label)}</div>
    <div class="latency-row-val">${fmtMs(lb[s.key])}</div>
  `).join('');

  const div = stages.length > 0 ? `<div class="latency-divider"></div>` : '';

  const totalRow = totalMs !== null ? `
    <div class="latency-row-label latency-total-label">Server End-to-End</div>
    <div class="latency-row-val latency-total-val ${underTarget ? 'under-target' : 'over-target'}">${fmtMs(totalMs)}</div>
  ` : '';

  const banner = totalMs !== null ? `
    <div class="latency-badge-banner ${underTarget ? 'ok' : 'warning'}">
      ${underTarget
        ? `✓ Under ${CONFIG.latencyTarget} ms target (${fmtMs(totalMs)})`
        : `⚠ Above ${CONFIG.latencyTarget} ms target (${fmtMs(totalMs)})`}
    </div>
  ` : '';

  const rtRow = `
    <div class="latency-row-label" style="font-size:.76rem;color:var(--color-text-faint)">Client Roundtrip</div>
    <div class="latency-row-val"   style="font-size:.76rem;color:var(--color-text-faint)">${fmtMs(frontendRoundtrip)}</div>
  `;

  const demoNote = CONFIG.demoMode ? `
    <div style="grid-column:1/-1;margin-top:6px;font-size:.72rem;color:var(--color-text-faint);font-style:italic;">
      * Simulated latency with ±12% jitter. Real numbers from live backend.
    </div>
  ` : '';

  DOM.latencyGrid.innerHTML = rows + div + totalRow + banner + rtRow + demoNote;
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
  u.onend  = () => DOM.btnSpeakAnswer.classList.remove('active');
  u.onerror = () => DOM.btnSpeakAnswer.classList.remove('active');
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
   12. HEALTH CHECK (silently falls back to demo mode)
══════════════════════════════════════════════════════════════ */

async function checkHealth() {
  if (CONFIG.demoMode) { updateDemoUI(); return; }
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
  DOM.settingApiUrl.value  = CONFIG.apiBase;
  DOM.settingTopK.value    = CONFIG.topK;
  DOM.topKVal.textContent  = CONFIG.topK;
  if (DOM.settingDemoMode) DOM.settingDemoMode.checked = CONFIG.demoMode;
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
  CONFIG.demoMode = DOM.settingDemoMode?.checked ?? CONFIG.demoMode;
  localStorage.setItem('hh_goa_api_base', CONFIG.apiBase);
  localStorage.setItem('hh_goa_top_k',    CONFIG.topK);
  localStorage.setItem('hh_goa_demo',     CONFIG.demoMode);
  DOM.settingsModal.style.display = 'none';
  updateDemoUI();
  checkHealth();
});

/* ══════════════════════════════════════════════════════════════
   14. EVENT WIRING
══════════════════════════════════════════════════════════════ */

DOM.btnMic.addEventListener('click', () => {
  if (currentState === State.RECORDING) {
    stopRecording();
  } else if ([State.IDLE, State.ANSWER, State.NO_CONTEXT,
               State.STT_ERROR, State.RETRIEVAL_ERROR,
               State.GEN_ERROR, State.NO_SPEECH].includes(currentState)) {
    startRecording();
  }
});

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
updateDemoUI();
checkHealth();
