# Financial Health Copilot — Phase 0

**From Transactions to Action.** Phase 0 implements the development foundation from [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md): a Next.js frontend, FastAPI backend, PostgreSQL migration, signup/login, protected empty dashboard, centralized configuration and CI checks.

**Only Phase 0 is implemented.** Account entry, CSV import, sample personas, financial metrics, forecasts, recommendations, simulation and AI chat belong to later phases. There are no fabricated dashboard numbers or placeholder financial endpoints. No AI API key is needed yet.

## Start locally

Prerequisites: Docker Desktop with Docker Compose v2, and Python 3 to generate the local environment file. On macOS, start Docker Desktop before the following commands.

```bash
cd financial-health-copilot-phase0
python3 scripts/setup_env.py
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000), select **Create an account**, use a demo email and a passphrase of at least 12 characters, then view the empty dashboard. Log out and log in again to verify your account.

- Frontend: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- API liveness: `http://localhost:8000/health`
- Database/migration readiness: `http://localhost:8000/ready`

`setup_env.py` generates separate local database and JWT secrets, never prints them, and will not overwrite an existing `.env`. The database starts first; a one-shot migration service completes; then the API and frontend start. An exited migration container with code 0 is expected.

This local setup binds ports to the loopback interface. It is not a public production deployment. Tokens stay in browser memory; refreshing the page signs you out. The stored account remains available for the next login.

## Implemented endpoints

| Method | Path | Access |
|---|---|---|
| POST | `/api/v1/auth/signup` | Public, rate-limited |
| POST | `/api/v1/auth/login` | Public, rate-limited |
| GET | `/api/v1/users/me` | Verified bearer JWT |
| GET | `/health` | Public liveness |
| GET | `/ready` | Public readiness; no credentials exposed |

The remaining endpoints in the original API specification are future requirements, not implemented routes.

## Project layout

| Path | Purpose |
|---|---|
| `frontend/src/app/` | Login/signup, protected empty dashboard and global style tokens |
| `frontend/src/components/auth-provider.tsx` | In-memory session and React Query provider |
| `frontend/tests/` | Real signup/login browser flow |
| `backend/app/auth/` | Validation, account creation, login and bounded rate limiter |
| `backend/app/core/` | Single configuration module, database, security and errors |
| `backend/app/db/` | User ORM model and initial Alembic migration |
| `backend/tests/` | Authentication, configuration and migration checks |
| `docker/` | Local database-role initialization |
| `scripts/setup_env.py` | Safe local environment generation |
| `.github/workflows/ci.yml` | Lint, types, Compose, tests and migration round trip |
| `docs/` | Original supplied requirements plus Phase 0 implementation notes |

## Test and review

```bash
docker compose exec backend pytest -q
docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q'
```

The first command runs isolated auth/config tests and skips database-specific tests unless `TEST_DATABASE_URL` is set. The second includes checks against the migrated local PostgreSQL database. Tests create only temporary test records in a rolled-back transaction. Browser tests create demo accounts; use a disposable test database for repeated runs.

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npx playwright install chromium
npm run test:e2e
```

The browser tests expect the stack on ports 3000/8000. See [Phase 0 setup](docs/PHASE_0_SETUP.md), [review results](docs/PHASE_0_REVIEW.md), and [implementation decisions](docs/PHASE_0_DECISIONS.md).

## Original project documents

Start with [product requirements](docs/PRODUCT_REQUIREMENTS.md), [implementation plan](docs/IMPLEMENTATION_PLAN.md), [configuration](docs/CONFIGURATION.md), [database schema](docs/DATABASE_SCHEMA.md), and [UI/UX design](docs/UI_UX_DESIGN.md). The original root README is preserved as [PROJECT_README.md](docs/PROJECT_README.md). The original `core md files/` directory is organized as `docs/`; document content is preserved unchanged.

The original `LOCAL_SETUP.md` describes the completed product, including seeding and financial features. Use **PHASE_0_SETUP.md for commands supported by this delivery**.
