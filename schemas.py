"""
Pydantic models shared across the PromptToMotion API.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    LOTTIE = "lottie"
    CSS = "css"
    CANVAS = "canvas"
    WEBM = "webm"
    MP4 = "mp4"


class MotionStyle(str, Enum):
    WAVES = "waves"
    PARTICLES = "particles"
    GRADIENT_FLOW = "gradient_flow"
    GLOW_ORBS = "glow_orbs"
    GRID_PULSE = "grid_pulse"
    NOISE_FIELD = "noise_field"


class FineTuneParams(BaseModel):
    """Real-time controls exposed on the Visual Fine-Tuner Dashboard."""
    speed: float = Field(1.0, ge=0.1, le=5.0, description="Animation speed multiplier")
    opacity: float = Field(0.9, ge=0.0, le=1.0)
    primary_color: str = Field("#8B5CF6", description="Primary neon accent (hex)")
    secondary_color: str = Field("#22D3EE", description="Secondary neon accent (hex)")
    background_color: str = Field("#0b0813", description="Base background color")
    particle_density: int = Field(60, ge=0, le=500)
    blur: float = Field(0.0, ge=0.0, le=40.0)
    loop: bool = True
    responsive: bool = True


class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=500,
                         example="Glowing deep purple futuristic neon waves with slow floating particles")
    formats: List[ExportFormat] = Field(default_factory=lambda: [ExportFormat.CSS])
    params: Optional[FineTuneParams] = None


class GeneratedAsset(BaseModel):
    format: ExportFormat
    filename: str
    content: Optional[str] = None       # inline text payload (css/js/lottie json)
    download_url: Optional[str] = None  # used for binary payloads (webm/mp4)
    mime_type: str


class PromptAnalysis(BaseModel):
    style: MotionStyle
    keywords: List[str]
    palette: List[str]
    intensity: float


class GenerateResponse(BaseModel):
    job_id: str
    analysis: PromptAnalysis
    params: FineTuneParams
    assets: List[GeneratedAsset]


class RenderJobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class RenderJob(BaseModel):
    job_id: str
    status: RenderJobStatus
    progress: int = 0
    format: ExportFormat
    download_url: Optional[str] = None
