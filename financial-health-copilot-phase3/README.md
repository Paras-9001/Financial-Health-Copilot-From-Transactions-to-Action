# Financial Health Copilot — Phase 3

**From Transactions to Action.** Phase 3 adds deterministic recurring-payment detection and an explainable cash-flow forecast to the corrected Phase 2 analytics foundation. Forecasts combine scheduled income, recurring expenses, loan installments, trailing unscheduled spending, a capped trend adjustment, and widening confidence bounds.

**Phases 0–3 are implemented.** Risks, recommendations, simulation and AI chat remain later phases. The frontend still shows the early dashboard because Phase 6 owns the complete visualization UI. All implemented APIs can be exercised through `/docs`. No AI API key is needed.

## Start locally

Prerequisites: Docker Desktop with Docker Compose v2, and Python 3 to generate the local environment file. Start Docker Desktop before running these commands.

```bash
cd financial-health-copilot-phase3-corrected
python scripts/setup_env.py
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000), create an account, then use [http://localhost:8000/docs](http://localhost:8000/docs) to inspect analytics, recurring expenses, and cash-flow forecasts.

- Frontend: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- API liveness: `http://localhost:8000/health` (reports `{"status": "ok", "phase": 3}`)
- Database/migration readiness: `http://localhost:8000/ready`

## Phase 3 quick verification

```bash
docker compose exec backend pytest -q
docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q'
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
```

To seed demo data and query financial metrics:
```bash
docker compose exec backend python scripts/seed_demo_data.py --persona all
```

Log in as `ananya.demo@example.com` (password `demo-passphrase-2026`) and call:

- `GET /api/v1/recurring-expenses`
- `GET /api/v1/cash-flow/forecast?horizon_days=30`

The forecast is labeled as a prediction, reports its assumptions and confidence inputs, and returns 30 daily chart points by default.

## Implemented endpoint groups

| Group | Paths |
|---|---|
| Authentication | `/api/v1/auth/*`, `/api/v1/users/me` |
| Manual entry | `/api/v1/accounts`, `/loans`, `/credit-cards`, `/income-sources` |
| Transactions | `GET/POST /api/v1/transactions`, `PATCH /api/v1/transactions/{id}` |
| Taxonomy | `GET /api/v1/categories` |
| CSV import | `/api/v1/imports/csv/preview`, `/api/v1/imports/csv/confirm` |
| Demo onboarding | `GET /api/v1/onboarding/personas`, `POST /api/v1/onboarding/demo` |
| Financial Analytics | `GET /api/v1/financial-summary`, `GET /api/v1/spending/by-category`, `GET /api/v1/debt/summary`, `GET /api/v1/debt/loans/{id}/amortization` |
| Recurring Expenses | `GET /api/v1/recurring-expenses` |
| Forecasting | `GET /api/v1/cash-flow/forecast` |
| Operations | `/health`, `/ready` |

## Project layout

| Path | Purpose |
|---|---|
| `backend/app/analytics/` | Deterministic financial analytics functions, schemas, repository and API router |
| `backend/app/recurring/` | Pure recurring-pattern detection, persistence and API |
| `backend/app/forecast/` | Deterministic forecast calculations, persistence and API |
| `backend/app/accounts/`, `transactions/`, `loans/`, `credit_cards/`, `income_sources/` | Thin routers, schemas and repositories |
| `backend/app/csv_import/`, `onboarding/`, `categorization/` | Import, persona and deterministic enrichment services |
| `backend/app/core/` | Single configuration module, database, security and errors |
| `backend/app/db/` | ORM models including `FinancialSnapshot` and Alembic migrations |
| `backend/tests/test_analytics.py` | Unit and API tests plus hand-computed fixtures for all three personas |
| `backend/tests/test_forecast.py` | Forecast, recurrence, confidence, persistence and three-persona tests |
| `docs/` | Architecture documentation and Phase 0–3 reviews/setup guides |
