/* ============================================================
   PromptToMotion — frontend logic
   Mirrors the backend's analyze/generate contract so the live
   preview updates instantly client-side; falls back to calling
   the FastAPI backend for Lottie JSON and video export jobs.
   ============================================================ */
(() => {
  "use strict";

  const API_BASE = window.PTM_API_BASE || "http://localhost:8000";

  // ---------- DOM ----------
  const $ = (sel) => document.querySelector(sel);
  const promptForm = $("#ptm-prompt-form");
  const promptInput = $("#ptm-prompt-input");
  const styleLabel = $("#ptm-style-label");
  const canvas = $("#ptm-canvas");
  const cssScene = $("#ptm-css-scene");
  const renderNote = $("#ptm-render-note");
  const codeOutput = $("#ptm-code-output");
  const codeFilename = $("#ptm-code-filename");
  const copyBtn = $("#ptm-copy-btn");
  const exportStatus = $("#ptm-export-status");
  const tabs = document.querySelectorAll(".ptm-tab");

  const ctrl = {
    speed: $("#ctrl-speed"),
    opacity: $("#ctrl-opacity"),
    density: $("#ctrl-density"),
    color1: $("#ctrl-color1"),
    color2: $("#ctrl-color2"),
    bg: $("#ctrl-bg"),
    responsive: $("#ctrl-responsive"),
  };
  const val = {
    speed: $("#val-speed"),
    opacity: $("#val-opacity"),
    density: $("#val-density"),
  };

  // ---------- state ----------
  let state = {
    analysis: null,
    params: readParams(),
    activeTab: "css",
  };

  function readParams() {
    return {
      speed: parseFloat(ctrl.speed.value),
      opacity: parseInt(ctrl.opacity.value, 10) / 100,
      particle_density: parseInt(ctrl.density.value, 10),
      primary_color: ctrl.color1.value,
      secondary_color: ctrl.color2.value,
      background_color: ctrl.bg.value,
      responsive: ctrl.responsive.checked,
    };
  }

  // ================================================================
  // 1. Prompt analysis (client-side mirror of services/prompt_parser.py)
  // ================================================================
  const STYLE_KEYWORDS = {
    waves: ["wave", "waves", "ocean", "flow", "ripple", "fluid"],
    particles: ["particle", "particles", "dust", "sparkle", "float", "floating", "snow"],
    gradient_flow: ["gradient", "aurora", "blend", "mesh"],
    glow_orbs: ["glow", "orb", "orbs", "bokeh", "light", "neon"],
    grid_pulse: ["grid", "matrix", "cyber", "circuit", "pulse"],
    noise_field: ["noise", "static", "texture", "smoke", "fog"],
  };

  const COLOR_WORDS = {
    "deep purple": "#6D28D9", "purple": "#8B5CF6", "violet": "#A855F7",
    "cyan": "#22D3EE", "blue": "#3B82F6", "teal": "#14B8A6",
    "pink": "#EC4899", "magenta": "#D946EF", "green": "#22C55E",
    "orange": "#F97316", "red": "#EF4444", "gold": "#EAB308",
  };

  const INTENSITY_WORDS = {
    slow: -0.3, calm: -0.3, gentle: -0.2, soft: -0.2,
    fast: 0.4, energetic: 0.3, intense: 0.4, chaotic: 0.5,
    futuristic: 0.15, cyber: 0.2,
  };

  function analyzePrompt(prompt) {
    const lowered = prompt.toLowerCase();
    const tokens = lowered.match(/[a-z]+/g) || [];

    let bestStyle = "glow_orbs", bestScore = 0;
    for (const [style, words] of Object.entries(STYLE_KEYWORDS)) {
      const score = words.reduce((s, w) => s + (lowered.includes(w) ? 1 : 0), 0);
      if (score > bestScore) { bestScore = score; bestStyle = style; }
    }

    const palette = [];
    for (const [phrase, hex] of Object.entries(COLOR_WORDS)) {
      if (lowered.includes(phrase) && !palette.includes(hex)) palette.push(hex);
    }
    if (palette.length === 0) palette.push("#8B5CF6", "#22D3EE");
    if (palette.length === 1) palette.push("#22D3EE");

    let intensity = 0.5;
    for (const [w, d] of Object.entries(INTENSITY_WORDS)) if (tokens.includes(w)) intensity += d;
    intensity = Math.max(0.1, Math.min(1, intensity));

    return { style: bestStyle, palette: palette.slice(0, 4), intensity: Math.round(intensity * 100) / 100, keywords: [...new Set(tokens)].slice(0, 12) };
  }

  // ================================================================
  // 2. Canvas renderer (mirrors services/css_generator.generate_canvas_js)
  // ================================================================
  let rafId = null;
  let particles = [];

  function resizeCanvas() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.getContext("2d").setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  window.addEventListener("resize", resizeCanvas);

  function seedParticles() {
    const rect = canvas.getBoundingClientRect();
    const count = state.analysis.style === "particles"
      ? Math.max(10, state.params.particle_density)
      : Math.min(state.params.particle_density, 90);
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * rect.width,
      y: Math.random() * rect.height,
      r: 1 + Math.random() * (state.analysis.style === "glow_orbs" ? 26 : 3),
      vx: (Math.random() - 0.5) * 0.6,
      vy: (Math.random() - 0.5) * 0.6,
      colorIdx: Math.random() > 0.5 ? 0 : 1,
      alpha: 0.25 + Math.random() * 0.55,
    }));
  }

  function renderFrame() {
    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    const { primary_color, secondary_color, background_color, speed, opacity } = state.params;
    const colors = [primary_color, secondary_color];

    ctx.fillStyle = background_color;
    ctx.fillRect(0, 0, rect.width, rect.height);

    for (const p of particles) {
      p.x += p.vx * speed;
      p.y += p.vy * speed;
      if (p.x < -20 || p.x > rect.width + 20) p.vx *= -1;
      if (p.y < -20 || p.y > rect.height + 20) p.vy *= -1;

      ctx.beginPath();
      ctx.globalAlpha = p.alpha * opacity;
      ctx.fillStyle = colors[p.colorIdx];
      if (state.analysis.style === "glow_orbs") {
        const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r);
        grad.addColorStop(0, colors[p.colorIdx]);
        grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad;
      }
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    rafId = requestAnimationFrame(renderFrame);
  }

  function startCanvas() {
    if (rafId) cancelAnimationFrame(rafId);
    resizeCanvas();
    seedParticles();
    renderFrame();
  }

  // ================================================================
  // 3. Code generators (mirrors services/css_generator.py, lightweight)
  // ================================================================
  function generateCSS() {
    const { primary_color: c1, secondary_color: c2, background_color: bg, speed, opacity, responsive } = state.params;
    const dur = Math.max(2, (14 / Math.max(speed, 0.1))).toFixed(2);
    return `.ptm-scene {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: ${bg};
}
.ptm-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(30px);
  opacity: ${opacity};
  mix-blend-mode: screen;
  animation: ptm-orb-move ${dur}s ease-in-out infinite;
}
.ptm-orb--a { width: 45%; height: 45%; left: 5%; top: 10%; background: ${c1}; }
.ptm-orb--b { width: 35%; height: 35%; right: 5%; bottom: 8%; background: ${c2}; animation-delay: -${(dur/2).toFixed(2)}s; }

@keyframes ptm-orb-move {
  0%   { transform: translate(0,0) scale(1); }
  50%  { transform: translate(6%, -8%) scale(1.15); }
  100% { transform: translate(0,0) scale(1); }
}
${responsive ? "\n@media (max-width: 640px) {\n  .ptm-scene { border-radius: 0; }\n}" : ""}`;
  }

  function generateCanvasJS() {
    const { primary_color: c1, secondary_color: c2, background_color: bg, speed, opacity, particle_density } = state.params;
    return `// PromptToMotion — Canvas renderer
(function () {
  const canvas = document.getElementById('ptm-canvas');
  const ctx = canvas.getContext('2d');
  const COLORS = ['${c1}', '${c2}'];
  const BG = '${bg}';
  const COUNT = ${particle_density};
  const SPEED = ${speed};

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = canvas.clientWidth * dpr;
    canvas.height = canvas.clientHeight * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  window.addEventListener('resize', resize);
  resize();

  const particles = Array.from({ length: COUNT }, () => ({
    x: Math.random() * canvas.clientWidth,
    y: Math.random() * canvas.clientHeight,
    r: 1 + Math.random() * 3,
    vx: (Math.random() - 0.5) * 0.3 * SPEED,
    vy: (Math.random() - 0.5) * 0.3 * SPEED,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
  }));

  (function frame() {
    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    for (const p of particles) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > canvas.clientWidth) p.vx *= -1;
      if (p.y < 0 || p.y > canvas.clientHeight) p.vy *= -1;
      ctx.globalAlpha = ${opacity};
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }
    requestAnimationFrame(frame);
  })();
})();`;
  }

  function generateEmbed() {
    return `<!-- PromptToMotion embed: drop into any page -->
<div id="ptm-scene" style="width:100%;height:420px;"></div>
<canvas id="ptm-canvas" style="width:100%;height:100%;"></canvas>
<script src="${API_BASE}/api/embed/${encodeURIComponent(promptInput.value.slice(0, 60))}.js"></script>
<!-- Or self-host: copy the Canvas/JS tab output into your own <script> tag. -->`;
  }

  // ================================================================
  // 4. UI wiring
  // ================================================================
  function refreshCodePanel() {
    const generators = { css: generateCSS, canvas: generateCanvasJS, embed: generateEmbed };
    const filenames = { css: "ptm-animation.css", canvas: "ptm-canvas.js", embed: "embed-snippet.html", lottie: "ptm-animation.json" };

    codeFilename.textContent = filenames[state.activeTab];

    if (state.activeTab === "lottie") {
      codeOutput.textContent = "// Fetching Lottie JSON from the backend...";
      fetchLottie();
      return;
    }
    codeOutput.textContent = generators[state.activeTab]();
  }

  async function fetchLottie() {
    try {
      const res = await fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: promptInput.value, formats: ["lottie"], params: state.params }),
      });
      if (!res.ok) throw new Error("backend unavailable");
      const data = await res.json();
      const asset = data.assets.find((a) => a.format === "lottie");
      codeOutput.textContent = asset ? asset.content : "// No Lottie asset returned.";
    } catch (err) {
      codeOutput.textContent = `// Backend not reachable at ${API_BASE}.\n// Start it with: uvicorn main:app --reload --port 8000\n// (Lottie JSON is generated server-side in services/lottie_generator.py)`;
    }
  }

  function applyPrompt(promptText) {
    promptInput.value = promptText;
    state.analysis = analyzePrompt(promptText);
    styleLabel.textContent = state.analysis.style;

    // Derive sensible defaults from the prompt if user hasn't manually tuned colors
    ctrl.color1.value = state.analysis.palette[0];
    ctrl.color2.value = state.analysis.palette[1];
    const derivedSpeed = Math.min(3, Math.max(0.2, 0.6 + state.analysis.intensity * 1.4));
    ctrl.speed.value = derivedSpeed.toFixed(1);
    val.speed.textContent = `${derivedSpeed.toFixed(1)}×`;

    state.params = readParams();
    startCanvas();
    refreshCodePanel();
    renderNote.textContent = `Live Canvas preview · style: ${state.analysis.style}`;
  }

  promptForm.addEventListener("submit", (e) => {
    e.preventDefault();
    applyPrompt(promptInput.value.trim() || promptInput.placeholder);
  });

  document.querySelectorAll(".ptm-chip").forEach((chip) => {
    chip.addEventListener("click", () => applyPrompt(chip.dataset.prompt));
  });

  // Fine-tuner listeners
  ctrl.speed.addEventListener("input", () => { val.speed.textContent = `${parseFloat(ctrl.speed.value).toFixed(1)}×`; state.params = readParams(); refreshCodePanel(); });
  ctrl.opacity.addEventListener("input", () => { val.opacity.textContent = `${ctrl.opacity.value}%`; state.params = readParams(); refreshCodePanel(); });
  ctrl.density.addEventListener("input", () => { val.density.textContent = ctrl.density.value; state.params = readParams(); seedParticles(); refreshCodePanel(); });
  [ctrl.color1, ctrl.color2, ctrl.bg, ctrl.responsive].forEach((el) =>
    el.addEventListener("input", () => { state.params = readParams(); refreshCodePanel(); })
  );

  // Tabs
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("is-active"));
      tab.classList.add("is-active");
      state.activeTab = tab.dataset.format;
      refreshCodePanel();
    });
  });

  // Copy button
  copyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(codeOutput.textContent);
      copyBtn.textContent = "Copied";
      copyBtn.classList.add("is-copied");
      setTimeout(() => { copyBtn.textContent = "Copy code"; copyBtn.classList.remove("is-copied"); }, 1600);
    } catch {
      exportStatus.textContent = "Clipboard blocked — select and copy manually.";
    }
  });

  // Video export (WebM/MP4) — polls the FastAPI job endpoint
  document.querySelectorAll("[data-export]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const format = btn.dataset.export;
      exportStatus.textContent = "Queuing render job...";
      try {
        const res = await fetch(`${API_BASE}/api/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: promptInput.value, formats: [format], params: state.params }),
        });
        if (!res.ok) throw new Error("generate failed");
        const data = await res.json();
        const asset = data.assets.find((a) => a.format === format);
        const jobId = asset.download_url.split("/").pop();
        pollJob(jobId, format);
      } catch {
        exportStatus.textContent = `Backend not reachable at ${API_BASE}. Start the FastAPI server to enable video export.`;
      }
    });
  });

  async function pollJob(jobId, format) {
    exportStatus.textContent = `Rendering ${format.toUpperCase()}… 0%`;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
        const job = await res.json();
        exportStatus.textContent = `Rendering ${format.toUpperCase()}… ${job.progress}%`;
        if (job.status === "done") {
          clearInterval(interval);
          exportStatus.textContent = `Ready → GET ${API_BASE}${job.download_url}`;
        } else if (job.status === "failed") {
          clearInterval(interval);
          exportStatus.textContent = "Render failed. Check backend logs.";
        }
      } catch {
        clearInterval(interval);
        exportStatus.textContent = "Lost connection to backend.";
      }
    }, 500);
  }

  // ---------- init ----------
  applyPrompt(promptInput.value);
})();
