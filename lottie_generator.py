"""
Produces a minimal, valid Lottie JSON animation (renderable by lottie-web)
parameterized from the prompt analysis and fine-tune controls.

This uses simple shape layers with looping keyframes so the output is
guaranteed to be spec-compliant, rather than trying to hand-roll a full
after-effects-grade export.
"""
from __future__ import annotations

from typing import Any, Dict

from models.schemas import PromptAnalysis, FineTuneParams, MotionStyle


def _hex_to_lottie_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return [round(r, 4), round(g, 4), round(b, 4), 1]


def generate_lottie(analysis: PromptAnalysis, params: FineTuneParams) -> Dict[str, Any]:
    fps = 30
    duration_s = max(2, round(6 / max(params.speed, 0.1)))
    frames = fps * duration_s

    color1 = _hex_to_lottie_rgb(params.primary_color)
    color2 = _hex_to_lottie_rgb(params.secondary_color)

    n_shapes = 3 if analysis.style != MotionStyle.PARTICLES else min(12, max(4, params.particle_density // 10))

    layers = []
    for i in range(n_shapes):
        color = color1 if i % 2 == 0 else color2
        x0 = 200 + i * 60
        y0 = 300
        layers.append({
            "ddd": 0,
            "ind": i + 1,
            "ty": 4,
            "nm": f"ptm_shape_{i+1}",
            "sr": 1,
            "ks": {
                "o": {"a": 0, "k": round(params.opacity * 100, 1)},
                "r": {"a": 0, "k": 0},
                "p": {
                    "a": 1,
                    "k": [
                        {"t": 0, "s": [x0, y0], "e": [x0 + 40, y0 - 60],
                         "i": {"x": [0.42], "y": [0]}, "o": {"x": [0.58], "y": [1]}},
                        {"t": frames / 2, "s": [x0 + 40, y0 - 60], "e": [x0, y0],
                         "i": {"x": [0.42], "y": [0]}, "o": {"x": [0.58], "y": [1]}},
                        {"t": frames, "s": [x0, y0]},
                    ],
                },
                "a": {"a": 0, "k": [0, 0]},
                "s": {"a": 0, "k": [100, 100]},
            },
            "ao": 0,
            "shapes": [
                {
                    "ty": "el",
                    "p": {"a": 0, "k": [0, 0]},
                    "s": {"a": 0, "k": [90, 90]},
                    "nm": "ellipse",
                },
                {
                    "ty": "fl",
                    "c": {"a": 0, "k": color},
                    "o": {"a": 0, "k": round(params.opacity * 100, 1)},
                    "nm": "fill",
                },
                {
                    "ty": "tr",
                    "p": {"a": 0, "k": [0, 0]},
                    "a": {"a": 0, "k": [0, 0]},
                    "s": {"a": 0, "k": [100, 100]},
                    "r": {"a": 0, "k": 0},
                    "o": {"a": 0, "k": 100},
                },
            ],
            "ip": 0,
            "op": frames,
            "st": 0,
            "bm": 0,
        })

    lottie = {
        "v": "5.9.6",
        "fr": fps,
        "ip": 0,
        "op": frames,
        "w": 800,
        "h": 600,
        "nm": f"PromptToMotion_{analysis.style.value}",
        "ddd": 0,
        "assets": [],
        "layers": layers,
        "markers": [],
        "meta": {
            "g": "PromptToMotion",
            "style": analysis.style.value,
            "keywords": analysis.keywords,
        },
    }
    return lottie
