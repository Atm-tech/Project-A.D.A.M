# ADAM - Data Management & Automation System

Local-first, deterministic data engine. Cloud optional. AI is advisory only.

## Layout
- `ADAM/backend/` - FastAPI service, data ingestion/processing, Celery worker.
- `ADAM/frontend/` - Lightweight upload dashboard (static HTML/JS).

## Run backend
```bash
cd ADAM/backend
python -m venv .venv
.\.venv\Scripts\activate          # on Windows PowerShell
pip install -r requirements.txt
uvicorn app.main:app --reload
```
API will mount at `settings.API_V1_PREFIX` (see `app/core/config.py`).

To run background worker:
```bash
cd ADAM/backend
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

## Local dashboard
Simple static dashboard is at `ADAM/frontend/index.html`. Serve it (so fetch works with CORS default):
```bash
cd ADAM/frontend
python -m http.server 4173
```
Then open http://localhost:4173 in a browser. API base defaults to `http://localhost:8000/api/v1`; change `API_BASE` in browser console if needed.

## Architecture guardrails
- Follow layers: Input + Processing + Rule Engine + AI (fallback) + Storage + Service + Presentation.
- Prefer rule-based validation and normalization; log all ingestion, transforms, and failures.
- AI usage: only when rule confidence is low; always log input, AI response, and final decision.
- Keep background/long jobs off the request thread; use workers/queues when added.

## Next steps (suggested)
1) Scaffold admin UI in `ADAM/frontend/` (Next.js + Tailwind) once data contracts are fixed.
2) Add ingestion logging and rule-engine hooks around existing endpoints (e.g., `app/api/v1/pkb_routes.py`).
3) Document data contracts (schemas, validation rules) alongside endpoints to enforce traceability.
