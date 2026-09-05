"""
Generates copy-paste CSS3 and Canvas/JS snippets from a PromptAnalysis +
FineTuneParams. Each generator is style-aware (waves, particles, glow_orbs...)
so the output actually matches what the user described.
"""
from __future__ import annotations

from models.schemas import PromptAnalysis, FineTuneParams, MotionStyle


def _duration(speed: float) -> float:
    # higher speed -> shorter duration, clamped to a sane range
    return round(max(2.0, 14.0 / max(speed, 0.1)), 2)


def generate_css(analysis: PromptAnalysis, params: FineTuneParams) -> str:
    c1, c2 = (params.primary_color, params.secondary_color)
    bg = params.background_color
    dur = _duration(params.speed)
    op = params.opacity
    blur = params.blur

    if analysis.style == MotionStyle.WAVES:
        body = f"""
.ptm-scene {{
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: {bg};
  isolation: isolate;
}}
.ptm-wave {{
  position: absolute;
  left: -20%;
  width: 140%;
  height: 60%;
  bottom: -20%;
  border-radius: 44%;
  opacity: {op};
  filter: blur({blur}px);
  animation: ptm-wave-motion {dur}s ease-in-out infinite;
}}
.ptm-wave--one {{ background: {c1}; animation-delay: 0s; }}
.ptm-wave--two {{ background: {c2}; opacity: {round(op * 0.7, 2)}; animation-delay: -{round(dur/3,2)}s; }}
.ptm-wave--three {{ background: {c1}; opacity: {round(op * 0.4, 2)}; animation-delay: -{round(dur/1.5,2)}s; }}

@keyframes ptm-wave-motion {{
  0%   {{ transform: translateY(0) rotate(0deg); }}
  50%  {{ transform: translateY(-6%) rotate(3deg); }}
  100% {{ transform: translateY(0) rotate(0deg); }}
}}
""".strip()

    elif analysis.style == MotionStyle.PARTICLES:
        body = f"""
.ptm-scene {{
  position: relative;
  width: 100%;
  height: 100%;
  background: {bg};
  overflow: hidden;
}}
.ptm-particle {{
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: radial-gradient(circle, {c1} 0%, {c2} 60%, transparent 100%);
  opacity: {op};
  filter: blur({round(blur/4, 1)}px);
  animation: ptm-float {dur}s ease-in-out infinite;
}}
@keyframes ptm-float {{
  0%   {{ transform: translateY(0) translateX(0) scale(1); opacity: {op}; }}
  50%  {{ transform: translateY(-40px) translateX(12px) scale(1.4); opacity: {round(op*0.6,2)}; }}
  100% {{ transform: translateY(0) translateX(0) scale(1); opacity: {op}; }}
}}
/* Generate N particles with staggered position/delay via JS - see ptm-canvas.js,
   or duplicate .ptm-particle elements with inline --x/--y/--delay custom props. */
.ptm-particle {{
  left: var(--x, 50%);
  top: var(--y, 50%);
  animation-delay: var(--delay, 0s);
}}
""".strip()

    elif analysis.style == MotionStyle.GRID_PULSE:
        body = f"""
.ptm-scene {{
  position: relative;
  width: 100%;
  height: 100%;
  background: {bg};
  background-image:
    linear-gradient({c1}22 1px, transparent 1px),
    linear-gradient(90deg, {c2}22 1px, transparent 1px);
  background-size: 40px 40px;
  animation: ptm-grid-pulse {dur}s linear infinite;
  opacity: {op};
  filter: blur({blur}px);
}}
@keyframes ptm-grid-pulse {{
  0%   {{ background-position: 0 0; filter: brightness(1); }}
  50%  {{ background-position: 40px 40px; filter: brightness(1.4); }}
  100% {{ background-position: 0 0; filter: brightness(1); }}
}}
""".strip()

    elif analysis.style == MotionStyle.NOISE_FIELD:
        body = f"""
.ptm-scene {{
  position: relative;
  width: 100%;
  height: 100%;
  background:
    radial-gradient(circle at 30% 30%, {c1}33, transparent 60%),
    radial-gradient(circle at 70% 70%, {c2}33, transparent 60%),
    {bg};
  filter: blur({max(blur, 6)}px) contrast(1.1);
  opacity: {op};
  animation: ptm-drift {dur}s ease-in-out infinite alternate;
}}
@keyframes ptm-drift {{
  0%   {{ transform: scale(1) translate(0,0); }}
  100% {{ transform: scale(1.15) translate(-3%, 2%); }}
}}
""".strip()

    else:  # GLOW_ORBS / GRADIENT_FLOW default
        body = f"""
.ptm-scene {{
  position: relative;
  width: 100%;
  height: 100%;
  background: {bg};
  overflow: hidden;
}}
.ptm-orb {{
  position: absolute;
  border-radius: 50%;
  filter: blur({max(blur, 30)}px);
  opacity: {op};
  mix-blend-mode: screen;
  animation: ptm-orb-move {dur}s ease-in-out infinite;
}}
.ptm-orb--a {{
  width: 45%; height: 45%; left: 5%; top: 10%;
  background: {c1};
}}
.ptm-orb--b {{
  width: 35%; height: 35%; right: 5%; bottom: 8%;
  background: {c2};
  animation-delay: -{round(dur/2,2)}s;
}}
@keyframes ptm-orb-move {{
  0%   {{ transform: translate(0,0) scale(1); }}
  50%  {{ transform: translate(6%, -8%) scale(1.15); }}
  100% {{ transform: translate(0,0) scale(1); }}
}}
""".strip()

    responsive = """
@media (max-width: 640px) {
  .ptm-scene { border-radius: 0; }
}
""".strip() if params.responsive else ""

    return f"{body}\n\n{responsive}".strip()


def generate_canvas_js(analysis: PromptAnalysis, params: FineTuneParams) -> str:
    """Generates a self-contained Canvas2D renderer (no external deps)."""
    c1, c2 = params.primary_color, params.secondary_color
    bg = params.background_color
    density = params.particle_density if analysis.style == MotionStyle.PARTICLES else min(params.particle_density, 120)
    speed = params.speed

    return f"""
// PromptToMotion - Canvas renderer
// Style: {analysis.style.value} | Generated from prompt analysis
(function () {{
  const canvas = document.getElementById('ptm-canvas');
  const ctx = canvas.getContext('2d');
  const DPR = Math.min(window.devicePixelRatio || 1, 2);
  const COLORS = ['{c1}', '{c2}'];
  const BG = '{bg}';
  const SPEED = {speed};
  const COUNT = {density};

  function resize() {{
    canvas.width = canvas.clientWidth * DPR;
    canvas.height = canvas.clientHeight * DPR;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }}
  window.addEventListener('resize', resize);
  resize();

  const particles = Array.from({{ length: COUNT }}, () => ({{
    x: Math.random() * canvas.clientWidth,
    y: Math.random() * canvas.clientHeight,
    r: 1 + Math.random() * 3,
    vx: (Math.random() - 0.5) * 0.3 * SPEED,
    vy: (Math.random() - 0.5) * 0.3 * SPEED,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
    alpha: 0.3 + Math.random() * 0.5,
  }}));

  function frame() {{
    const w = canvas.clientWidth, h = canvas.clientHeight;
    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, w, h);

    for (const p of particles) {{
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > w) p.vx *= -1;
      if (p.y < 0 || p.y > h) p.vy *= -1;

      ctx.beginPath();
      ctx.globalAlpha = p.alpha * {params.opacity};
      ctx.fillStyle = p.color;
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }}
    ctx.globalAlpha = 1;
    requestAnimationFrame(frame);
  }}
  requestAnimationFrame(frame);
}})();
""".strip()
