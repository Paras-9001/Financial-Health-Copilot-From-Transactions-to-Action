# Local Setup Guide

The README gives a one-glance overview; this is the actual step-by-step a developer follows to get the full stack running.

## Prerequisites

- Docker + Docker Compose
- Node.js 20+ (only needed if running frontend outside Docker for hot-reload development)
- Python 3.11+ (only needed if running backend outside Docker)
- An LLM provider API key (e.g., Anthropic API key)

## Directory Structure

```
.
├── backend/
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── data/
│   └── seed/                # persona CSV/JSON fixtures (SAMPLE_DATA.md)
├── docs/                     # this documentation package
├── docker-compose.yml
├── .env.example
└── scripts/
    └── seed_demo_data.py
```

## Step-by-Step: Full Stack via Docker Compose (recommended)

```bash
git clone <repo-url>
cd financial-health-copilot

cp .env.example .env
# edit .env and set:
#   LLM_API_KEY=your_key_here
#   DATABASE_URL=postgresql://postgres:postgres@db:5432/financial_copilot
#   JWT_SECRET=generate_a_random_string

docker compose up --build
```

This starts three services:
- `db` — PostgreSQL on `localhost:5432`
- `backend` — FastAPI on `localhost:8000` (interactive API docs at `localhost:8000/docs`)
- `frontend` — Next.js on `localhost:3000`

## Step-by-Step: Seed Demo Data

```bash
docker compose exec backend python scripts/seed_demo_data.py --persona all
```
- `--persona all` seeds Ananya, Rohit, and Meera (`SAMPLE_DATA.md`).
- `--persona ananya` seeds a single persona for a faster iteration loop.
- Run this after the first `docker compose up` and any time you want a clean demo state (it's idempotent — re-running against the same user is safe due to `dedup_hash`, per `DATA_PIPELINES.md`).

## Step-by-Step: Database Migrations

```bash
docker compose exec backend alembic upgrade head          # apply migrations
docker compose exec backend alembic revision --autogenerate -m "description"  # after model changes
```

## Running Backend Tests

```bash
docker compose exec backend pytest                        # full suite
docker compose exec backend pytest tests/unit/test_analytics.py -v   # single file
docker compose exec backend pytest -k "financial_calculation"        # by keyword
```

## Running Frontend Locally (hot reload, outside Docker)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

## Running Backend Locally (outside Docker)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Environment Variables Reference

| Variable | Where used | Example |
|---|---|---|
| `DATABASE_URL` | backend | `postgresql://postgres:postgres@localhost:5432/financial_copilot` |
| `JWT_SECRET` | backend (auth) | random 32+ char string |
| `LLM_API_KEY` | backend (agent module) | provider-issued key |
| `LLM_MODEL` | backend (agent module) | e.g. `claude-sonnet-4-6` |
| `NEXT_PUBLIC_API_URL` | frontend | `http://localhost:8000` |

## Verifying the Setup

1. Visit `localhost:8000/docs` — the FastAPI auto-generated OpenAPI UI should list every endpoint in `API_SPECIFICATION.md`.
2. Visit `localhost:3000`, sign up, choose "Explore with sample data" → Ananya (`ONBOARDING_AND_DATA_IMPORT.md`).
3. Dashboard should show a health score, at least one risk, and at least one recommendation within a couple seconds.
4. Run `docker compose exec backend pytest` — the financial calculation test suite should pass 100%.

## Common Issues

| Symptom | Likely cause | Fix |
|---|---|---|
| Backend can't connect to DB | `db` service not ready yet | Compose healthcheck/retry; wait a few seconds and retry, or add a `depends_on` with `condition: service_healthy` |
| Chat endpoint returns 503 | Missing/invalid `LLM_API_KEY` | Check `.env`, dashboard/analytics endpoints should still work independently |
| Seed script says "duplicates skipped: N" on first run | Script run twice, or fixtures already loaded | Expected/idempotent behavior, not an error |
| Frontend shows CORS error | `NEXT_PUBLIC_API_URL` mismatch or backend CORS origin not set to frontend's URL | Check backend CORS middleware config matches frontend origin |
