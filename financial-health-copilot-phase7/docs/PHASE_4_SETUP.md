# Phase 4 Setup and Verification (Docker)

## Start

Create a local environment file and start the stack:

```bash
python scripts/setup_env.py
docker compose up --build -d
docker compose ps
```

The migration service must reach Alembic revision `0003_phase4`. Then verify:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Expected responses are `{"status":"ok","phase":4}` and `{"status":"ready"}`.

## Test

```bash
docker compose exec backend pytest -q
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
```

Run PostgreSQL-gated migration tests inside Docker:

```bash
docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q'
```

## Seed and inspect

```bash
docker compose exec backend python scripts/seed_demo_data.py --persona all
```

Open `http://localhost:8000/docs`, authenticate, then exercise `/risks`,
`/recommendations`, `/simulate`, and `/affordability/check`.

Stop without deleting the database volume:

```bash
docker compose down
```
