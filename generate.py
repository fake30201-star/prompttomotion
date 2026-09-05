from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from models.schemas import (
    PromptRequest, GenerateResponse, GeneratedAsset, ExportFormat,
    FineTuneParams, RenderJob,
)
from services.prompt_parser import analyze_prompt
from services.css_generator import generate_css, generate_canvas_js
from services.lottie_generator import generate_lottie
from services.video_renderer import create_job, render_video_job, get_job

router = APIRouter(prefix="/api", tags=["generate"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(payload: PromptRequest, background_tasks: BackgroundTasks):
    """
    Core Prompt-to-Motion endpoint. Analyzes the prompt, applies fine-tune
    params (or sensible defaults derived from the prompt), and returns
    ready-to-copy assets for every requested format. Video formats return
    a job_id-backed asset that resolves asynchronously via /api/jobs/{id}.
    """
    if not payload.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt cannot be empty.")

    analysis = analyze_prompt(payload.prompt)

    # If the client didn't supply fine-tune params, derive sensible defaults
    # from the prompt analysis (palette + intensity -> speed/opacity).
    params = payload.params or FineTuneParams(
        primary_color=analysis.palette[0],
        secondary_color=analysis.palette[1] if len(analysis.palette) > 1 else analysis.palette[0],
        speed=round(0.6 + analysis.intensity * 1.4, 2),
        opacity=round(0.6 + analysis.intensity * 0.3, 2),
    )

    assets = []
    for fmt in payload.formats:
        if fmt == ExportFormat.CSS:
            assets.append(GeneratedAsset(
                format=fmt, filename="ptm-animation.css",
                content=generate_css(analysis, params), mime_type="text/css",
            ))
        elif fmt == ExportFormat.CANVAS:
            assets.append(GeneratedAsset(
                format=fmt, filename="ptm-canvas.js",
                content=generate_canvas_js(analysis, params), mime_type="application/javascript",
            ))
        elif fmt == ExportFormat.LOTTIE:
            import json
            lottie_json = generate_lottie(analysis, params)
            assets.append(GeneratedAsset(
                format=fmt, filename="ptm-animation.json",
                content=json.dumps(lottie_json), mime_type="application/json",
            ))
        elif fmt in (ExportFormat.WEBM, ExportFormat.MP4):
            job = create_job(fmt)
            background_tasks.add_task(render_video_job, job.job_id)
            assets.append(GeneratedAsset(
                format=fmt, filename=f"ptm-loop.{fmt.value}",
                download_url=f"/api/jobs/{job.job_id}",
                mime_type="video/webm" if fmt == ExportFormat.WEBM else "video/mp4",
            ))

    return GenerateResponse(
        job_id=uuid.uuid4().hex[:10],
        analysis=analysis,
        params=params,
        assets=assets,
    )


@router.get("/jobs/{job_id}", response_model=RenderJob)
async def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("/preview")
async def preview(payload: PromptRequest):
    """Lightweight endpoint for the live-preview pane: analysis + CSS only, no jobs."""
    analysis = analyze_prompt(payload.prompt)
    params = payload.params or FineTuneParams(
        primary_color=analysis.palette[0],
        secondary_color=analysis.palette[1] if len(analysis.palette) > 1 else analysis.palette[0],
    )
    return JSONResponse({
        "analysis": analysis.model_dump(),
        "css": generate_css(analysis, params),
        "params": params.model_dump(),
    })
