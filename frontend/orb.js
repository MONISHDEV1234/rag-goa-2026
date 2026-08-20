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
    let frameId;

    /* ── hook into app.js state transitions ── */
    // We'll monkey-patch DOM.btnMic class changes
    const origClassAdd = canvas.classList.add.bind(canvas.classList);
    const origClassRemove = canvas.classList.remove.bind(canvas.classList);

    canvas.classList.add = function(...args) {
      origClassAdd(...args);
      if (args.includes('recording')) {
        isRecording = true;
        const micLabel = document.getElementById('mic-label');
        if (micLabel) { micLabel.classList.add('listening'); }
      }
    };
    canvas.classList.remove = function(...args) {
      origClassRemove(...args);
      if (args.includes('recording')) {
        isRecording = false;
        const micLabel = document.getElementById('mic-label');
        if (micLabel) { micLabel.classList.remove('listening'); }
      }
    };

    /* ── expose setAnalyser for app.js audio pipeline ── */
    window.orbSetAnalyser = function(a, d) { analyser = a; dataArr = d; };

    /* ── click handler ── */
    canvas.addEventListener('click', () => {
      // find and click the real hidden btn or call app.js mic toggle
      const realBtn = document.getElementById('btn-mic-real');
      if (realBtn) realBtn.click();
      // also dispatch a custom event app.js can listen to
      canvas.dispatchEvent(new CustomEvent('orb-click', { bubbles: true }));
    });

    canvas.addEventListener('keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        canvas.click();
      }
    });

    /* ── render loop ── */
    function draw(ts) {
      frameId = requestAnimationFrame(draw);

      /* rotation speeds — faster when recording */
      const speed = isRecording ? 1.8 : 1.0;
      ax += 0.0025 * speed;
      ay += 0.0041 * speed;
      az += 0.0018 * speed;

      /* read audio amplitude */
      if (analyser && dataArr) {
        analyser.getByteFrequencyData(dataArr);
        const avg = dataArr.reduce((s, v) => s + v, 0) / dataArr.length;
        const target = avg / 128;              // 0-2, clamp to 0-1.5
        amplitude += (Math.min(target, 1.5) - amplitude) * 0.18;  // smooth
      } else {
        amplitude += (0 - amplitude) * 0.08;  // decay when silent
      }

      /* spawn audio-reactive particles */
      if (isRecording && amplitude > 0.05) {
        const count = Math.floor(amplitude * 12);
        spawnParticles(count, scale * (0.8 + amplitude * 0.6), cx, cy);
      }

      /* clear */
      ctx.clearRect(0, 0, W, H);

      /* ── 1. project vertices ── */
      const projected = VERTS.map(v => {
        let p = rotX(v, ax);
        p = rotY(p, ay);
        p = rotZ(p, az);
        return project(p, cx, cy, scale, FOV);
      });

      /* ── 2. draw particles behind orb ── */
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x  += p.vx;
        p.y  += p.vy;
        p.life -= p.decay;
        p.vx *= 0.97;
        p.vy *= 0.97;
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

      /* ── 3. draw soft glow halo ── */
      const haloR = scale * (0.72 + amplitude * 0.28);
      const haloAlpha = 0.08 + amplitude * 0.18;
      const halo = ctx.createRadialGradient(cx, cy, 0, cx, cy, haloR * 1.6);
      halo.addColorStop(0, `rgba(255, 200, 40, ${haloAlpha * 2})`);
      halo.addColorStop(0.5, `rgba(255, 160, 20, ${haloAlpha})`);
      halo.addColorStop(1, `rgba(255, 140, 10, 0)`);
      ctx.beginPath();
      ctx.arc(cx, cy, haloR * 1.6, 0, Math.PI * 2);
      ctx.fillStyle = halo;
      ctx.fill();

      /* ── 4. draw wireframe edges ── */
      ctx.save();
      ctx.lineWidth = 0.7;

      EDGES.forEach(([i, j]) => {
        const [ax2, ay2, az2] = projected[i];
        const [bx, by, bz] = projected[j];

        // depth-based brightness
        const depthA = (az2 + 1) / 2;   // 0=back, 1=front
        const depthB = (bz + 1) / 2;
        const depth  = (depthA + depthB) / 2;

        // audio-reactive brightness boost
        const boost  = isRecording ? amplitude * 0.4 : 0;
        const bright = Math.min(1, depth * 0.7 + 0.3 + boost);
        const alpha  = 0.15 + bright * 0.7;

        // front edges bright gold, back edges dim amber
        let color;
        if (depth > 0.65) {
          color = `rgba(255, 205, 50, ${alpha})`;    // bright gold front
        } else if (depth > 0.35) {
          color = `rgba(220, 155, 30, ${alpha * 0.7})`;  // mid amber
        } else {
          color = `rgba(120, 80, 10, ${alpha * 0.4})`;   // dim back
        }

        ctx.beginPath();
        ctx.moveTo(ax2, ay2);
        ctx.lineTo(bx, by);
        ctx.strokeStyle = color;
        ctx.stroke();
      });

      ctx.restore();

      /* ── 5. audio-reactive spikes from surface ── */
      if (isRecording && amplitude > 0.08 && dataArr) {
        const numSpikes = 24;
        ctx.save();
        for (let k = 0; k < numSpikes; k++) {
          const angle = (k / numSpikes) * Math.PI * 2;
          const baseR = scale * 0.72;
          const spikeLen = amplitude * scale * 0.45 * (0.3 + 0.7 * Math.random());
          const x1 = cx + Math.cos(angle) * baseR;
          const y1 = cy + Math.sin(angle) * baseR;
          const x2 = cx + Math.cos(angle) * (baseR + spikeLen);
          const y2 = cy + Math.sin(angle) * (baseR + spikeLen);

          const grd = ctx.createLinearGradient(x1, y1, x2, y2);
          grd.addColorStop(0, `rgba(255, 220, 60, ${0.85 * amplitude})`);
          grd.addColorStop(1, `rgba(255, 180, 20, 0)`);

          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.strokeStyle = grd;
          ctx.lineWidth = 1.2 + amplitude * 1.5;
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
