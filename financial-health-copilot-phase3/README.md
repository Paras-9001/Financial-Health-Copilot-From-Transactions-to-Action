# Financial Health Copilot — Phase 2

**From Transactions to Action.** Phase 2 adds the deterministic Financial Analytics Engine to the data layer: pure calculation functions for all formulas in `FINANCIAL_ANALYTICS.md`, composite 0–100 health scoring, explainable confidence labeling, persistent `financial_snapshots`, and endpoints for `/financial-summary`, `/spending/by-category`, `/debt/summary`, and `/debt/loans/{id}/amortization`.

**Phases 0, 1, and 2 are implemented.** Forecasting, risks, recommendations, simulation and AI chat remain later phases. The Phase 0 frontend still shows the empty dashboard; Phase 6 owns the financial summary dashboard UI. All Phase 2 financial analytics endpoints are usable through the API at `/docs`. No AI API key is needed.

## Start locally

Prerequisites: Docker Desktop with Docker Compose v2, and Python 3 to generate the local environment file. On macOS, start Docker Desktop before the following commands.

```bash
cd financial-health-copilot-phase2
python3 scripts/setup_env.py
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000), create an account, then use [http://localhost:8000/docs](http://localhost:8000/docs) to view financial summaries, category breakdowns, debt details, and loan amortization.

- Frontend: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- API liveness: `http://localhost:8000/health` (reports `{"status": "ok", "phase": 2}`)
- Database/migration readiness: `http://localhost:8000/ready`

## Phase 2 quick verification

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

Log in as `ananya.demo@example.com` (password `demo-passphrase-2026`) and call `GET /api/v1/financial-summary` to inspect:
- Income: ₹60,000.00
- Expenses: ₹48,000.00
- Savings: ₹12,000.00
- Savings Rate: 20.00%
- Debt-to-Income (DTI): 15.80%
- Recurring Burden: 46.70%
- Credit Utilization: 22.00%
- Health Score: 71 (High confidence)

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
| Operations | `/health`, `/ready` |

## Project layout

| Path | Purpose |
|---|---|
| `backend/app/analytics/` | Deterministic financial analytics functions, schemas, repository and API router |
| `backend/app/accounts/`, `transactions/`, `loans/`, `credit_cards/`, `income_sources/` | Thin routers, schemas and repositories |
| `backend/app/csv_import/`, `onboarding/`, `categorization/` | Import, persona and deterministic enrichment services |
| `backend/app/core/` | Single configuration module, database, security and errors |
| `backend/app/db/` | ORM models including `FinancialSnapshot` and Alembic migrations |
| `backend/tests/test_analytics.py` | 21 unit & integration tests verifying 100% of financial formulas & endpoints |
| `docs/` | Complete architectural documentation and Phase 0/1/2 reviews |
