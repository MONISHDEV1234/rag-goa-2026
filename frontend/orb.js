/**
 * orb.js — Golden Wireframe AI Orb Engine
 *
 * Renders a continuously rotating icosahedron-based geodesic wireframe
 * in warm golden color on the #btn-mic canvas.
 *
 * When recording, the Web Audio API drives amplitude-reactive yellow
 * light particles that expand and brighten with loudness.
 */

(function () {
  'use strict';

  /* ── Color palette ──────────────────────────────────────────── */
  const GOLD_BRIGHT   = '#ffd966';
  const GOLD_MID      = '#e8a620';
  const GOLD_DIM      = '#8a5a0a';
  const PARTICLE_HUE  = 48;   // yellow-gold

  /* ── Icosahedron + subdivisions ─────────────────────────────── */
  const PHI = (1 + Math.sqrt(5)) / 2;

  // 12 base vertices of a unit icosahedron
  const BASE_VERTS = [
    [-1,  PHI, 0], [ 1,  PHI, 0], [-1, -PHI, 0], [ 1, -PHI, 0],
    [ 0, -1,  PHI], [ 0,  1,  PHI], [ 0, -1, -PHI], [ 0,  1, -PHI],
    [ PHI, 0, -1], [ PHI, 0,  1], [-PHI, 0, -1], [-PHI, 0,  1],
  ].map(v => { const l = Math.hypot(...v); return v.map(c => c / l); });

  const BASE_FACES = [
    [0,11,5],[0,5,1],[0,1,7],[0,7,10],[0,10,11],
    [1,5,9],[5,11,4],[11,10,2],[10,7,6],[7,1,8],
    [3,9,4],[3,4,2],[3,2,6],[3,6,8],[3,8,9],
    [4,9,5],[2,4,11],[6,2,10],[8,6,7],[9,8,1],
  ];

  function midpoint(a, b) {
    const m = [(a[0]+b[0])/2, (a[1]+b[1])/2, (a[2]+b[2])/2];
    const l = Math.hypot(...m); return m.map(c => c / l);
  }

  function subdivide(verts, faces, depth) {
    for (let d = 0; d < depth; d++) {
      const newFaces = [];
      const cache = {};
      function getMid(i, j) {
        const key = i < j ? `${i}_${j}` : `${j}_${i}`;
        if (!cache[key]) { verts.push(midpoint(verts[i], verts[j])); cache[key] = verts.length - 1; }
        return cache[key];
      }
      faces.forEach(([a, b, c]) => {
        const ab = getMid(a, b), bc = getMid(b, c), ca = getMid(c, a);
        newFaces.push([a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]);
      });
      faces = newFaces;
    }
    return { verts, faces };
  }

  const { verts: VERTS, faces: FACES } = subdivide(
    BASE_VERTS.map(v => [...v]),
    BASE_FACES.map(f => [...f]),
    2   // subdivision depth — 2 gives ~320 faces, enough detail
  );

  // Build edge set (no duplicates)
  const edgeSet = new Set();
  const EDGES = [];
  FACES.forEach(([a, b, c]) => {
    [[a,b],[b,c],[c,a]].forEach(([i, j]) => {
      const key = i < j ? `${i}_${j}` : `${j}_${i}`;
      if (!edgeSet.has(key)) { edgeSet.add(key); EDGES.push([i, j]); }
    });
  });

  /* ── 3-D rotation helpers ───────────────────────────────────── */
  function rotX(v, a) {
    const [x, y, z] = v, c = Math.cos(a), s = Math.sin(a);
    return [x, y*c - z*s, y*s + z*c];
  }
  function rotY(v, a) {
    const [x, y, z] = v, c = Math.cos(a), s = Math.sin(a);
    return [x*c + z*s, y, -x*s + z*c];
  }
  function rotZ(v, a) {
    const [x, y, z] = v, c = Math.cos(a), s = Math.sin(a);
    return [x*c - y*s, x*s + y*c, z];
  }

  function project(v, cx, cy, scale, fov) {
    const z = v[2] + fov;
    const f = fov / z;
    return [cx + v[0] * scale * f, cy + v[1] * scale * f, v[2]];
  }

  /* ── Particle system ────────────────────────────────────────── */
  const MAX_PARTICLES = 160;
  const particles = [];

  function spawnParticles(amount, radius, cx, cy) {
    for (let i = 0; i < amount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const dist  = radius * (0.6 + Math.random() * 0.6);
      particles.push({
        x: cx + Math.cos(angle) * dist,
        y: cy + Math.sin(angle) * dist,
        vx: (Math.random() - 0.5) * 2.5,
        vy: (Math.random() - 0.5) * 2.5,
        r: 1.5 + Math.random() * 3,
        alpha: 0.7 + Math.random() * 0.3,
        life: 1.0,
        decay: 0.012 + Math.random() * 0.025,
      });
    }
    // trim
    while (particles.length > MAX_PARTICLES) particles.shift();
  }

  /* ── Main entry point ───────────────────────────────────────── */
  function initOrb() {
    const canvas = document.getElementById('btn-mic');
    if (!canvas || !(canvas instanceof HTMLCanvasElement)) return;

    const ctx = canvas.getContext('2d');
    const W = canvas.width;
    const H = canvas.height;
    const cx = W / 2, cy = H / 2;
    const scale = W * 0.38;
    const FOV   = 3.5;

    /* audio-analysis state */
    let analyser = null;
    let dataArr  = null;
    let amplitude = 0;          // 0-1 smoothed

    /* rotation state */
    let ax = 0, ay = 0, az = 0;
    let isRecording = false;
    let visualState = 'IDLE'; // 'IDLE' | 'RECORDING' | 'PROCESSING' | 'SPEAKING'
    let isSpeakingTTS = false;
    let frameId;

    /* morph state — 1 = full organic morph (idle), 0 = perfect shape (recording / processing) */
    let morphBlend = 0.0;

    // Per-vertex noise seeds — unique phase offsets so every vertex moves independently
    const NOISE_SEEDS = VERTS.map(() => ({
      f1: 0.4 + Math.random() * 0.5,   // freq 1
      f2: 0.9 + Math.random() * 0.8,   // freq 2
      f3: 1.6 + Math.random() * 1.2,   // freq 3
      p1: Math.random() * Math.PI * 2,
      p2: Math.random() * Math.PI * 2,
      p3: Math.random() * Math.PI * 2,
      amp: 0.06 + Math.random() * 0.10, // per-vertex morph strength
    }));

    /* ── hook into app.js state transitions ── */
    const origClassAdd    = canvas.classList.add.bind(canvas.classList);
    const origClassRemove = canvas.classList.remove.bind(canvas.classList);
    const origClassToggle = canvas.classList.toggle.bind(canvas.classList);

    function applyRecording(active) {
      isRecording = active;
      if (active) {
        visualState = 'RECORDING';
      } else if (visualState === 'RECORDING') {
        visualState = 'IDLE';
      }
      const micLabel = document.getElementById('mic-label');
      if (micLabel) micLabel.classList.toggle('listening', active);
    }

    canvas.classList.add = function(...args) {
      origClassAdd(...args);
      if (args.includes('recording')) applyRecording(true);
    };
    canvas.classList.remove = function(...args) {
      origClassRemove(...args);
      if (args.includes('recording')) applyRecording(false);
    };
    canvas.classList.toggle = function(cls, force) {
      const result = origClassToggle(cls, force);
      if (cls === 'recording') applyRecording(typeof force === 'boolean' ? force : result);
      return result;
    };

    // Watch only aria-pressed
    new MutationObserver(() => {
      const pressed = canvas.getAttribute('aria-pressed') === 'true';
      applyRecording(pressed);
    }).observe(canvas, { attributes: true, attributeFilter: ['aria-pressed'] });

    /* ── expose hooks for app.js audio pipeline & visual states ── */
    window.orbSetAnalyser = function(a, d) { analyser = a; dataArr = d; };
    window.orbSetState = function(state) {
      if (['IDLE', 'RECORDING', 'PROCESSING', 'SPEAKING'].includes(state)) {
        visualState = state;
      }
    };
    window.orbSetSpeaking = function(speaking) {
      isSpeakingTTS = !!speaking;
      if (isSpeakingTTS) visualState = 'SPEAKING';
      else if (visualState === 'SPEAKING') visualState = 'IDLE';
    };

    /* ── click handler ── */
    canvas.addEventListener('click', () => {
      if (window._orbAudioCtx && window._orbAudioCtx.state === 'suspended') {
        window._orbAudioCtx.resume();
      }
      const realBtn = document.getElementById('btn-mic-real');
      if (realBtn) realBtn.click();
      canvas.dispatchEvent(new CustomEvent('orb-click', { bubbles: true }));
    });

    canvas.addEventListener('keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); canvas.click(); }
    });

    /* ── Orbital vortex particles for PROCESSING state ── */
    const orbitalParticles = Array.from({ length: 36 }, (_, i) => ({
      angle: (i / 36) * Math.PI * 2,
      radius: scale * (1.1 + (i % 3) * 0.18),
      speed: 0.04 + (i % 4) * 0.015,
      tilt: 0.35 + (i % 2) * 0.2,
      size: 1.2 + (i % 3) * 0.8,
      hue: (i % 2 === 0) ? 48 : 38
    }));

    /* ── render loop ── */
    function draw(ts) {
      frameId = requestAnimationFrame(draw);

      const now = performance.now();
      const t   = now * 0.001;

      /* rotation — dynamic by state */
      let speed = 1.0;
      if (visualState === 'RECORDING') speed = 2.2;
      else if (visualState === 'PROCESSING') speed = 3.6;
      else if (visualState === 'SPEAKING') speed = 1.6;

      ax += 0.0025 * speed;
      ay += 0.0041 * speed;
      az += 0.0018 * speed;

      /* ── read audio amplitude (when recording) ── */
      if (analyser && dataArr) {
        analyser.getByteFrequencyData(dataArr);
        const len = dataArr.length;
        let weighted = 0, wTotal = 0;
        for (let i = 0; i < len; i++) {
          const w = (i < len * 0.5) ? 2.0 : 0.5;
          weighted += dataArr[i] * w;
          wTotal += w;
        }
        const avg = weighted / wTotal;
        const target = Math.min(avg / 90, 1.8);
        amplitude += (target - amplitude) * 0.22;
      } else {
        amplitude += (0 - amplitude) * 0.06;
      }

      /* ── spawn particles when speaking / processing ── */
      if (visualState === 'RECORDING' && amplitude > 0.08) {
        const count = Math.floor(2 + amplitude * 14);
        spawnParticles(count, scale * (0.85 + amplitude * 0.55), cx, cy);
      } else if (visualState === 'SPEAKING' && Math.random() > 0.6) {
        spawnParticles(1, scale * 1.05, cx, cy);
      }

      /* ── CLEAR ── */
      ctx.clearRect(0, 0, W, H);

      /* ── 1. ALWAYS-ON IDLE BREATHING GOLDEN AURA ── */
      const breathe = 0.95 + 0.08 * Math.sin(t * 1.4);
      const idleR   = scale * 1.05 * breathe;
      const idleAlpha = 0.12 + 0.04 * Math.sin(t * 1.4);
      const idleGrad  = ctx.createRadialGradient(cx, cy, scale * 0.3, cx, cy, idleR);
      idleGrad.addColorStop(0,   `rgba(255, 210, 60, ${idleAlpha * 1.4})`);
      idleGrad.addColorStop(0.45,`rgba(255, 165, 20, ${idleAlpha})`);
      idleGrad.addColorStop(1,   'rgba(200, 100, 0, 0)');
      ctx.beginPath();
      ctx.arc(cx, cy, idleR, 0, Math.PI * 2);
      ctx.fillStyle = idleGrad;
      ctx.fill();

      /* ── 2. STATE-SPECIFIC AURAS ── */
      if (visualState === 'RECORDING') {
        // Multi-layer loudness-driven aura
        const amp = amplitude;
        const coreR = scale * (0.82 + amp * 0.65);
        const coreA = Math.min(0.72, 0.18 + amp * 0.70);
        const gA = ctx.createRadialGradient(cx, cy, scale * 0.2, cx, cy, coreR);
        gA.addColorStop(0,   `rgba(255, 248, 130, ${coreA * 1.4})`);
        gA.addColorStop(0.25,`rgba(255, 220, 50,  ${coreA * 1.1})`);
        gA.addColorStop(0.6, `rgba(255, 160, 10,  ${coreA * 0.6})`);
        gA.addColorStop(1,   'rgba(220, 100, 0, 0)');
        ctx.beginPath();
        ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
        ctx.fillStyle = gA;
        ctx.fill();

        const midR = scale * (1.25 + amp * 1.0);
        const midA = Math.min(0.52, 0.08 + amp * 0.58);
        const gB = ctx.createRadialGradient(cx, cy, scale * 0.45, cx, cy, midR);
        gB.addColorStop(0,   `rgba(255, 230, 70, ${midA * 0.7})`);
        gB.addColorStop(0.35,`rgba(255, 175, 25, ${midA})`);
        gB.addColorStop(0.75,`rgba(240, 120, 5,  ${midA * 0.4})`);
        gB.addColorStop(1,   'rgba(180, 70, 0, 0)');
        ctx.beginPath();
        ctx.arc(cx, cy, midR, 0, Math.PI * 2);
        ctx.fillStyle = gB;
        ctx.fill();

        const outerR = scale * (1.7 + amp * 1.6);
        const outerA = Math.min(0.30, amp * 0.35);
        const gC = ctx.createRadialGradient(cx, cy, scale * 0.55, cx, cy, outerR);
        gC.addColorStop(0,   `rgba(255, 210, 50, ${outerA * 0.5})`);
        gC.addColorStop(0.4, `rgba(255, 145, 10, ${outerA})`);
        gC.addColorStop(0.8, `rgba(200, 80,  0,  ${outerA * 0.3})`);
        gC.addColorStop(1,   'rgba(120, 50, 0, 0)');
        ctx.beginPath();
        ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
        ctx.fillStyle = gC;
        ctx.fill();

        const shimmer = 0.12 + amp * 0.65 + 0.06 * Math.sin(now * 0.016);
        const ringR   = scale * (0.76 + amp * 0.2);
        ctx.beginPath();
        ctx.arc(cx, cy, ringR, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255, 240, 80, ${Math.min(0.9, shimmer)})`;
        ctx.lineWidth   = 1.5 + amp * 4.5;
        ctx.shadowBlur  = 20 + amp * 55;
        ctx.shadowColor = '#ffc820';
        ctx.stroke();
        ctx.shadowBlur  = 0;
      } else if (visualState === 'PROCESSING') {
        // High-energy golden synthesizing vortex aura
        const procPulse = 1.0 + 0.14 * Math.sin(t * 8.0);
        const procR = scale * 1.35 * procPulse;
        const gProc = ctx.createRadialGradient(cx, cy, 0, cx, cy, procR);
        gProc.addColorStop(0, 'rgba(255, 225, 80, 0.42)');
        gProc.addColorStop(0.5, 'rgba(255, 150, 20, 0.22)');
        gProc.addColorStop(1, 'rgba(180, 60, 0, 0)');
        ctx.beginPath();
        ctx.arc(cx, cy, procR, 0, Math.PI * 2);
        ctx.fillStyle = gProc;
        ctx.fill();

        // Draw orbital particle vortex ring
        orbitalParticles.forEach(op => {
          op.angle += op.speed;
          const ox = cx + Math.cos(op.angle) * op.radius;
          const oy = cy + Math.sin(op.angle) * (op.radius * Math.cos(op.tilt));
          const opAlpha = 0.4 + 0.5 * Math.sin(op.angle);
          if (opAlpha > 0.05) {
            ctx.beginPath();
            ctx.arc(ox, oy, op.size, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${op.hue}, 100%, 75%, ${opAlpha})`;
            ctx.shadowBlur = 8;
            ctx.shadowColor = '#ffd040';
            ctx.fill();
            ctx.shadowBlur = 0;
          }
        });
      } else if (visualState === 'SPEAKING') {
        // Harmonic undulating voice playback aura
        const speakWave = 1.0 + 0.22 * Math.sin(t * 6.5);
        const speakR    = scale * 1.3 * speakWave;
        const gSpeak = ctx.createRadialGradient(cx, cy, scale * 0.2, cx, cy, speakR);
        gSpeak.addColorStop(0, 'rgba(255, 240, 100, 0.38)');
        gSpeak.addColorStop(0.4, 'rgba(255, 180, 30, 0.22)');
        gSpeak.addColorStop(1, 'rgba(200, 90, 0, 0)');
        ctx.beginPath();
        ctx.arc(cx, cy, speakR, 0, Math.PI * 2);
        ctx.fillStyle = gSpeak;
        ctx.fill();
      }

      /* ── 3. PARTICLES ── */
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx; p.y += p.vy;
        p.life -= p.decay;
        p.vx *= 0.97; p.vy *= 0.97;
        if (p.life <= 0) { particles.splice(i, 1); continue; }
        const a = p.alpha * p.life;
        const r = p.r * (0.5 + p.life * 0.5);
        const grd = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r * 4);
        grd.addColorStop(0, `hsla(${PARTICLE_HUE}, 100%, 75%, ${a})`);
        grd.addColorStop(1, `hsla(${PARTICLE_HUE}, 100%, 55%, 0)`);
        ctx.beginPath();
        ctx.arc(p.x, p.y, r * 4, 0, Math.PI * 2);
        ctx.fillStyle = grd;
        ctx.fill();
      }

      /* ── 4. WIREFRAME ── */
      const isCrisp = (visualState === 'RECORDING' || visualState === 'PROCESSING');
      const morphTarget = isCrisp ? 0.0 : 1.0;
      const lerpRate    = morphTarget < morphBlend ? 0.10 : 0.022;
      morphBlend += (morphTarget - morphBlend) * lerpRate;

      const projected = VERTS.map((v, idx) => {
        const ns   = NOISE_SEEDS[idx];
        const noise =
          Math.sin(t * ns.f1 + ns.p1) * 0.4 +
          Math.sin(t * ns.f2 + ns.p2) * 0.35 +
          Math.sin(t * ns.f3 + ns.p3) * 0.25;
        const disp   = noise * ns.amp * morphBlend;
        let expand = 1;
        if (visualState === 'RECORDING') expand = (1 + amplitude * 0.12);
        else if (visualState === 'PROCESSING') expand = (1 + 0.05 * Math.sin(t * 10 + idx));
        else if (visualState === 'SPEAKING') expand = (1 + 0.06 * Math.sin(t * 6 + idx * 0.3));

        const morphed = [
          v[0] * (1 + disp) * expand,
          v[1] * (1 + disp) * expand,
          v[2] * (1 + disp) * expand,
        ];
        let p = rotX(morphed, ax);
        p = rotY(p, ay);
        p = rotZ(p, az);
        return project(p, cx, cy, scale, FOV);
      });

      ctx.save();
      ctx.lineWidth = 0.7;
      EDGES.forEach(([i, j], edgeIdx) => {
        const [ax2, ay2, az2] = projected[i];
        const [bx, by, bz]    = projected[j];
        const depthA = (az2 + 1) / 2;
        const depthB = (bz  + 1) / 2;
        const depth  = (depthA + depthB) / 2;

        let boost = 0;
        if (visualState === 'RECORDING') boost = amplitude * 0.45;
        else if (visualState === 'PROCESSING') boost = 0.35 * Math.abs(Math.sin(t * 8 + edgeIdx * 0.15));
        else if (visualState === 'SPEAKING') boost = 0.25 * Math.abs(Math.sin(t * 5 + (ax2 + bx) * 0.02));

        const bright = Math.min(1, depth * 0.7 + 0.3 + boost);
        const alpha  = 0.15 + bright * 0.7;
        let color;
        if (depth > 0.65)      color = `rgba(255, 205, 50,  ${alpha})`;
        else if (depth > 0.35) color = `rgba(220, 155, 30,  ${alpha * 0.7})`;
        else                   color = `rgba(120, 80,  10,  ${alpha * 0.4})`;
        ctx.beginPath();
        ctx.moveTo(ax2, ay2);
        ctx.lineTo(bx, by);
        ctx.strokeStyle = color;
        ctx.stroke();
      });
      ctx.restore();

      /* ── 5. AUDIO SPIKES (RECORDING ONLY) ── */
      if (visualState === 'RECORDING' && amplitude > 0.08 && dataArr) {
        const numSpikes = 32;
        ctx.save();
        for (let k = 0; k < numSpikes; k++) {
          const angle   = (k / numSpikes) * Math.PI * 2;
          const baseR   = scale * 0.74;
          const spikeLen = amplitude * scale * 0.55 * (0.25 + 0.75 * Math.random());
          const x1 = cx + Math.cos(angle) * baseR;
          const y1 = cy + Math.sin(angle) * baseR;
          const x2 = cx + Math.cos(angle) * (baseR + spikeLen);
          const y2 = cy + Math.sin(angle) * (baseR + spikeLen);
          const grd = ctx.createLinearGradient(x1, y1, x2, y2);
          grd.addColorStop(0, `rgba(255, 230, 60, ${0.9 * amplitude})`);
          grd.addColorStop(1, `rgba(255, 180, 20, 0)`);
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.strokeStyle = grd;
          ctx.lineWidth = 1.2 + amplitude * 2.0;
          ctx.stroke();
        }
        ctx.restore();
      }
    }

    draw(0);
  }

  /* ── Patch app.js mic event wiring ─────────────────────────── */
  // app.js references DOM.btnMic and calls startRecording() / stopRecording()
  // which use MediaRecorder. We intercept the click chain by overriding
  // the orb canvas click to also trigger the actual recording functions.
  //
  // app.js DOM.btnMic = getElementById('btn-mic')  → the canvas
  // The canvas now handles click → we fire it forward.

  function patchAppJs() {
    // Override startRecording to also expose analyser to orb
    const origStart = window.startRecording;
    if (typeof origStart === 'function') {
      window.startRecording = function(...args) {
        const result = origStart.apply(this, args);
        // After startRecording sets up the AudioContext, grab the analyser
        // app.js stores it as 'analyser' in closure — we'll detect it via event
        return result;
      };
    }

    // Listen for the orb-click event and forward to app.js mic toggle
    document.getElementById('btn-mic')?.addEventListener('orb-click', () => {
      // app.js wired a click listener to DOM.btnMic (the canvas)
      // so we just needed to make canvas clickable, which it is.
    });
  }

  // Also: patch app.js visual feedback helpers that toggle .recording class
  // on DOM.btnMic — those already work because DOM.btnMic IS the canvas,
  // and our classList.add/remove override above catches 'recording'.

  /* ── Audio context bridge ───────────────────────────────────── */
  // Expose a hook so app.js can hand us the analyser node after getUserMedia
  // We'll also auto-detect by polling window.sonarAnalyser (set by app.js below)
  function pollAnalyser() {
    if (window.sonarAnalyser && window.sonarDataArray) {
      window.orbSetAnalyser(window.sonarAnalyser, window.sonarDataArray);
    }
    setTimeout(pollAnalyser, 200);
  }

  /* ── Boot ───────────────────────────────────────────────────── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { initOrb(); pollAnalyser(); });
  } else {
    initOrb();
    pollAnalyser();
  }

})();
