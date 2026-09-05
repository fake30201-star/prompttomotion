"""
PromptToMotion - FastAPI backend entrypoint.

Run locally:
    cd backend
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Docs available at http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import generate

app = FastAPI(
    title="PromptToMotion API",
    description="Converts natural language prompts into web animations, CSS/Canvas code, Lottie JSON, and looping video.",
    version="1.0.0",
)

# Allow the frontend (served separately, e.g. Vite/static host) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your deployed frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router)


@app.get("/api/health", tags=["meta"])
async def health():
    return {"status": "ok", "service": "prompttomotion-api"}


# Optional: serve the static frontend directly from FastAPI for a single-process deploy.
# Comment out if you're hosting the frontend separately (Vercel/Netlify/nginx).
try:
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
except RuntimeError:
    pass
