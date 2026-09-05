"""
Video rendering pipeline for the WebM / MP4 export path.

Rendering a looping video from an animation definition is CPU/GPU heavy
(headless browser capture or frame-by-frame compositing + ffmpeg encode),
so it's modeled here as an async background job:

  1. POST /api/generate with formats=["webm"] -> returns job_id immediately
  2. Worker (this module) renders frames + encodes in the background
  3. Client polls GET /api/jobs/{job_id} until status == "done"
  4. GET /api/jobs/{job_id}/download streams the final file

In production, swap `_fake_render` for a real pipeline, e.g.:
  - Puppeteer/Playwright headless capture of the CSS/Canvas scene -> PNG frames
  - ffmpeg -framerate 30 -i frame_%04d.png -c:v libvpx-vp9 out.webm
  - ffmpeg -framerate 30 -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p out.mp4
This module keeps that swap isolated behind `render_video_job`.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Dict

from models.schemas import RenderJob, RenderJobStatus, ExportFormat

# In-memory job store. Replace with Redis/DB for multi-worker deployments.
JOBS: Dict[str, RenderJob] = {}


def create_job(export_format: ExportFormat) -> RenderJob:
    job_id = uuid.uuid4().hex[:12]
    job = RenderJob(job_id=job_id, status=RenderJobStatus.QUEUED, progress=0, format=export_format)
    JOBS[job_id] = job
    return job


async def render_video_job(job_id: str) -> None:
    """Simulated render pipeline; replace body with real ffmpeg/headless-capture calls."""
    job = JOBS.get(job_id)
    if not job:
        return
    job.status = RenderJobStatus.PROCESSING
    try:
        for pct in (10, 30, 55, 75, 90):
            await asyncio.sleep(0.4)
            job.progress = pct
        # --- real implementation would run ffmpeg here and produce a real file ---
        job.progress = 100
        job.status = RenderJobStatus.DONE
        ext = "webm" if job.format == ExportFormat.WEBM else "mp4"
        job.download_url = f"/api/jobs/{job_id}/download.{ext}"
    except Exception:
        job.status = RenderJobStatus.FAILED


def get_job(job_id: str) -> RenderJob | None:
    return JOBS.get(job_id)
