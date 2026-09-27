# Phase 2 Setup and Verification

## Upgrade from Phase 1

From the repository root:

```bash
cd financial-health-copilot-phase2
python3 scripts/setup_env.py
docker compose up --build -d
docker compose ps -a
```

The database applies migrations `0001_initial` and `0002_phase1`. `/ready` confirms database readiness and `/health` reports `{"status": "ok", "phase": 2}`.

## Verify

```bash
docker compose exec backend pytest -v
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
```

All 53 tests pass in the local/SQLite suite. Two PostgreSQL migration checks also run when
`TEST_DATABASE_URL` is provided (the second command above does this inside Docker).

## Seed Personas and Inspect Financial Summaries

```bash
docker compose exec backend python scripts/seed_demo_data.py --persona all
```

Open `http://localhost:8000/docs`, click **Authorize**, and paste the token from login.

Call:
1. `GET /api/v1/financial-summary` — returns facts, ratios, volatility, data-quality metadata, and the composite health score (71 for Persona A).
2. `GET /api/v1/spending/by-category` — returns spending grouped by category with percentages and types.
3. `GET /api/v1/debt/summary` — returns debt totals, DTI, credit utilization, and loans/cards breakdown.
4. `GET /api/v1/debt/loans/{id}/amortization` — returns month-by-month principal and interest amortization schedule.
