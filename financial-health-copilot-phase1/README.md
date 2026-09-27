# Financial Health Copilot — Phase 1

**From Transactions to Action.** Phase 1 adds the complete data layer to the Phase 0 foundation: domain models and repositories, authenticated manual-entry APIs, deterministic transaction ingestion and categorization, duplicate-safe demo seeding, and CSV preview/confirm importing with partial-row errors.

**Phases 0 and 1 are implemented.** Financial analytics, forecasts, risks, recommendations, simulation and AI chat remain later phases. The Phase 0 frontend still shows the honest empty dashboard; Phase 6 owns the onboarding UI. All Phase 1 onboarding modes are usable through the API at `/docs`. No AI API key is needed.

## Start locally

Prerequisites: Docker Desktop with Docker Compose v2, and Python 3 to generate the local environment file. On macOS, start Docker Desktop before the following commands.

```bash
cd financial-health-copilot-phase1
python3 scripts/setup_env.py
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000), create an account, then use [http://localhost:8000/docs](http://localhost:8000/docs) to add data manually, preview/confirm a CSV, or select a demo persona.

- Frontend: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- API liveness: `http://localhost:8000/health`
- Database/migration readiness: `http://localhost:8000/ready`

`setup_env.py` generates separate local database and JWT secrets, never prints them, and will not overwrite an existing `.env`. The database starts first; a one-shot migration service applies revisions `0001_initial` and `0002_phase1`; then the API and frontend start. An exited migration container with code 0 is expected.

## Phase 1 quick verification

```bash
docker compose exec backend pytest -q
docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q'
docker compose exec backend python scripts/seed_demo_data.py --persona all
docker compose exec backend python scripts/seed_demo_data.py --persona all
```

On the second seed run, each persona must report `0 imported` and all existing transactions as duplicates skipped. Demo accounts use `ananya.demo@example.com`, `rohit.demo@example.com`, and `meera.demo@example.com`; the development-only password defaults to `demo-passphrase-2026` and can be overridden with `DEMO_USER_PASSWORD`.

The CSV template is at [`data/seed/transactions-template.csv`](data/seed/transactions-template.csv). See [Phase 1 setup](docs/PHASE_1_SETUP.md) and [Phase 1 API](docs/PHASE_1_API.md).

This local setup binds ports to the loopback interface. It is not a public production deployment. Tokens stay in browser memory; refreshing the page signs you out. The stored account remains available for the next login.

## Implemented endpoint groups

| Group | Paths |
|---|---|
| Authentication | `/api/v1/auth/*`, `/api/v1/users/me` |
| Manual entry | `/api/v1/accounts`, `/loans`, `/credit-cards`, `/income-sources` |
| Transactions | `GET/POST /api/v1/transactions`, `PATCH /api/v1/transactions/{id}` |
| Taxonomy | `GET /api/v1/categories` |
| CSV import | `POST /api/v1/imports/csv/preview`, `POST /api/v1/imports/csv/confirm` |
| Demo onboarding | `GET /api/v1/onboarding/personas`, `POST /api/v1/onboarding/demo` |
| Operations | `/health`, `/ready` |

The analytics and AI endpoint groups in the original API specification remain future requirements.

## Project layout

| Path | Purpose |
|---|---|
| `frontend/src/app/` | Login/signup, protected empty dashboard and global style tokens |
| `frontend/src/components/auth-provider.tsx` | In-memory session and React Query provider |
| `frontend/tests/` | Real signup/login browser flow |
| `backend/app/auth/` | Validation, account creation, login and bounded rate limiter |
| `backend/app/core/` | Single configuration module, database, security and errors |
| `backend/app/db/` | Phase 1 ORM models and two explicit Alembic migrations |
| `backend/app/accounts`, `transactions`, `loans`, `credit_cards`, `income_sources` | Thin routers, schemas and repositories |
| `backend/app/csv_import`, `onboarding`, `categorization` | Import, persona and deterministic enrichment services |
| `backend/tests/` | Authentication, data isolation, imports, dedup, seed and migration checks |
| `docker/` | Local database-role initialization |
| `scripts/setup_env.py` | Safe local environment generation |
| `.github/workflows/ci.yml` | Lint, types, Compose, tests and migration round trip |
| `docs/` | Original requirements plus Phase 0/1 implementation notes |

## Test and review

```bash
docker compose exec backend pytest -q
docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q'
```

The first command runs isolated auth/config/data-layer tests and skips database-specific tests unless `TEST_DATABASE_URL` is set. The second includes checks against the migrated local PostgreSQL database. Tests create only temporary test records in a rolled-back transaction.

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npx playwright install chromium
npm run test:e2e
```

The browser tests expect the stack on ports 3000/8000. See [Phase 1 setup](docs/PHASE_1_SETUP.md), [Phase 1 API](docs/PHASE_1_API.md), and [Phase 0 decisions](docs/PHASE_0_DECISIONS.md).

## Original project documents

Start with [product requirements](docs/PRODUCT_REQUIREMENTS.md), [implementation plan](docs/IMPLEMENTATION_PLAN.md), [configuration](docs/CONFIGURATION.md), [database schema](docs/DATABASE_SCHEMA.md), and [UI/UX design](docs/UI_UX_DESIGN.md). The original root README is preserved as [PROJECT_README.md](docs/PROJECT_README.md). The original `core md files/` directory is organized as `docs/`; document content is preserved unchanged.

The original `LOCAL_SETUP.md` describes the completed product. Use **PHASE_1_SETUP.md for commands supported by this delivery**.
