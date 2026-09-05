"""
Prompt -> Motion analysis.

This is a lightweight, deterministic keyword parser so the whole stack runs
with zero external dependencies out of the box. Swap `analyze_prompt` for a
call to an LLM (e.g. Claude via the Anthropic API) to get richer, more
accurate style/palette extraction without changing any downstream code -
the contract (PromptAnalysis) stays the same.
"""
from __future__ import annotations

import re
from typing import List

from models.schemas import PromptAnalysis, MotionStyle

STYLE_KEYWORDS = {
    MotionStyle.WAVES: ["wave", "waves", "ocean", "flow", "ripple", "fluid"],
    MotionStyle.PARTICLES: ["particle", "particles", "dust", "sparkle", "float", "floating", "snow"],
    MotionStyle.GRADIENT_FLOW: ["gradient", "aurora", "blend", "mesh"],
    MotionStyle.GLOW_ORBS: ["glow", "orb", "orbs", "bokeh", "light", "neon"],
    MotionStyle.GRID_PULSE: ["grid", "matrix", "cyber", "circuit", "pulse"],
    MotionStyle.NOISE_FIELD: ["noise", "static", "texture", "smoke", "fog"],
}

COLOR_WORDS = {
    "purple": "#8B5CF6",
    "violet": "#A855F7",
    "deep purple": "#6D28D9",
    "cyan": "#22D3EE",
    "blue": "#3B82F6",
    "teal": "#14B8A6",
    "pink": "#EC4899",
    "magenta": "#D946EF",
    "green": "#22C55E",
    "orange": "#F97316",
    "red": "#EF4444",
    "gold": "#EAB308",
    "black": "#0b0813",
    "obsidian": "#0b0813",
    "white": "#F8FAFC",
}

INTENSITY_WORDS = {
    "slow": -0.3, "calm": -0.3, "gentle": -0.2, "soft": -0.2,
    "fast": 0.4, "energetic": 0.3, "intense": 0.4, "chaotic": 0.5,
    "futuristic": 0.15, "cyber": 0.2,
}


def _tokenize(prompt: str) -> List[str]:
    return re.findall(r"[a-zA-Z]+", prompt.lower())


def analyze_prompt(prompt: str) -> PromptAnalysis:
    lowered = prompt.lower()
    tokens = _tokenize(prompt)

    # 1. Determine dominant style by keyword hits
    scores = {style: 0 for style in MotionStyle}
    for style, words in STYLE_KEYWORDS.items():
        for w in words:
            if w in lowered:
                scores[style] += 1
    best_style = max(scores, key=scores.get)
    if scores[best_style] == 0:
        best_style = MotionStyle.GLOW_ORBS  # sensible default for a "motion" prompt

    # 2. Extract palette (ordered, deduped)
    palette: List[str] = []
    for phrase, hex_code in COLOR_WORDS.items():
        if phrase in lowered and hex_code not in palette:
            palette.append(hex_code)
    if not palette:
        palette = ["#8B5CF6", "#22D3EE"]
    if len(palette) == 1:
        palette.append("#22D3EE")

    # 3. Intensity baseline + modifiers
    intensity = 0.5
    for word, delta in INTENSITY_WORDS.items():
        if word in tokens:
            intensity += delta
    intensity = max(0.1, min(1.0, intensity))

    return PromptAnalysis(
        style=best_style,
        keywords=list(dict.fromkeys(tokens))[:12],
        palette=palette[:4],
        intensity=round(intensity, 2),
    )
