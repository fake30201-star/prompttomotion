# PromptToMotion

Convert a natural-language prompt into a looping web animation, then export it as
copy-paste CSS, Canvas/JS, Lottie JSON, or a rendered WebM/MP4 loop.

## Structure

```
prompttomotion/
├── backend/                  FastAPI service
│   ├── main.py                App entrypoint (CORS, routes, serves /frontend)
│   ├── models/schemas.py      Pydantic request/response contracts
│   ├── routers/generate.py    /api/generate, /api/preview, /api/jobs/{id}
│   ├── services/
│   │   ├── prompt_parser.py     Prompt -> style / palette / intensity
│   │   ├── css_generator.py     Style-aware CSS3 + Canvas code generator
│   │   ├── lottie_generator.py  Minimal valid Lottie JSON builder
│   │   └── video_renderer.py    Async render job queue (WebM/MP4 stub)
│   └── requirements.txt
└── frontend/                 Static UI (no build step)
    ├── index.html              Hero prompt bar, live preview, fine-tuner, integrator
    ├── css/style.css           Dark glassmorphism / neon design system
    └── js/app.js               Client-side analysis + Canvas renderer + API calls
```

## Run it

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

**Frontend**
The backend already mounts `../frontend` as static files, so opening
http://localhost:8000/ serves the full app. To develop the frontend
standalone instead (e.g. `npx serve frontend`), set the API base before
`app.js` loads:
```html
<script>window.PTM_API_BASE = "http://localhost:8000";</script>
```

## API surface

| Method | Route                    | Purpose                                             |
|--------|---------------------------|------------------------------------------------------|
| POST   | `/api/generate`           | Full prompt -> assets pipeline (css/canvas/lottie/webm/mp4) |
| POST   | `/api/preview`            | Lightweight analysis + CSS only, for live preview   |
| GET    | `/api/jobs/{job_id}`      | Poll a video render job's status/progress           |
| GET    | `/api/health`             | Liveness check                                      |

## Notes on the video pipeline

`services/video_renderer.py` models WebM/MP4 export as an async job so the
API stays responsive: it queues a job, returns a `job_id` immediately, and
the frontend polls `/api/jobs/{id}` until `status == "done"`. The actual
frame-capture + encode step is stubbed with a progress simulation — wire in
a headless-browser capture (Playwright) piped into `ffmpeg` where indicated
in that file's docstring to make it render real video.

## Extending prompt understanding

`services/prompt_parser.py` is a deterministic keyword matcher so the whole
stack runs with zero external API keys. Its output contract (`PromptAnalysis`)
is stable, so you can swap the function body for a call to an LLM (e.g. the
Anthropic API) to get richer style/palette extraction without touching any
downstream generator.
