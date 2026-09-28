# Phase 0 setup and developer handoff

## What you need

Recommended local route: Docker Desktop / Docker Engine with Compose v2 and Python 3 for environment generation. For non-Docker frontend development use Node.js 22+ and npm; for the backend use Python 3.12 (the source supports 3.11+) and PostgreSQL 16. No LLM account or key is required for this phase.

## Docker startup

From the project root:

```bash
python3 scripts/setup_env.py
docker compose up --build
```

Allow the initial dependency and image downloads to complete. The `db` service initializes two non-superuser roles: `fhc_owner` owns schema migrations; `fhc_app` has data access without schema creation. A separate `migrate` service runs Alembic and exits successfully. The backend process receives only the application database URL; migration credentials are not present in its environment. The frontend waits for backend readiness.

Visit `http://localhost:3000`. Signup requires a valid email-shaped demo address, a nonblank name, and a password/passphrase of at least 12 characters and no more than 72 UTF-8 bytes. The length cap prevents bcrypt truncation. Email uniqueness is case-insensitive because stored addresses are normalized to lowercase and the database enforces normalization.

Signup returns a token; the frontend then fetches `/users/me` and opens the dashboard. There are no seeded financial records. A fresh account shows “Your financial picture starts here”.

## Environment configuration

| Variable | Purpose | Phase 0 behavior |
|---|---|---|
| `POSTGRES_DB` | Database name | `financial_copilot` |
| `POSTGRES_PASSWORD` | Local bootstrap administrator credential | Generated; db container only |
| `MIGRATION_DB_PASSWORD` | Schema-owner credential | Generated; db initialization and migration service |
| `APP_DB_PASSWORD` | Runtime DML credential | Generated; db initialization and backend |
| `DATABASE_URL` | Local backend database URL | `postgresql+psycopg://` required; Compose substitutes hostname `db` |
| `MIGRATION_DATABASE_URL` | Local Alembic owner URL | Compose supplies separately to migration service |
| `JWT_SECRET` | JWT signing key | Generated, at least 32 characters; invalid placeholder stops startup |
| `CORS_ORIGINS` | JSON array of exact allowed browser origins | Default `["http://localhost:3000"]`; wildcard rejected |
| `NEXT_PUBLIC_API_URL` | Browser-facing API host | `http://localhost:8000`; build-time value |
| `ACCESS_TOKEN_MINUTES` | Optional token lifetime | 30; backend environment if overriding |
| `AUTH_RATE_LIMIT` | Optional attempts per client IP/window | 10 |
| `AUTH_RATE_WINDOW_SECONDS` | Optional rate window | 60 |
| `AUTH_RATE_MAX_CLIENTS` | Optional in-memory limiter bound | 10,000 |
| `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` | Optional Phase 5 model composition | Unused unless cloud consent is explicitly enabled |
| `AI_MODE` | `auto`, `fallback` or `llm` | `auto`; provider still requires key/model/consent |
| `CLOUD_AI_CONSENT_GRANTED` | Server-side opt-in for model calls | `false` |

For optional backend overrides in Docker, add them to `backend.environment` in Compose. Do not pass every `.env` variable to the runtime service: that would expose migration credentials unnecessarily. Generated secrets are hexadecimal so URLs need no extra encoding. If manually replacing a database password, URL-encode special characters in connection strings.

## Local hot-reload development

Start only the database and apply the migration:

```bash
docker compose up -d db
docker compose run --rm migrate
```

Backend, from a separate terminal:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000 --no-proxy-headers
```

The settings loader reads the generated root `.env` via `../.env`. Run this command from `backend/`. For Windows PowerShell use `.venv\Scripts\Activate.ps1` instead of `source`.

Frontend, in another terminal:

```bash
cd frontend
npm ci
cp .env.local.example .env.local
npm run dev
```

No financial domain dependencies are installed preemptively. Charting and financial data-processing libraries will be added with the phases that use them.

## Verification commands

From `backend/` with the virtual environment active:

```bash
ruff check .
ruff format --check .
pytest -q
alembic current
```

From `frontend/`:

```bash
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

For all database tests with Compose running:

```bash
docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q'
```

The CI workflow performs the same quality checks, a real Docker build/start, PostgreSQL tests, browser tests and a destructive migration round trip **only on its disposable CI database**. Do not run `alembic downgrade base` against data you intend to retain.

## Migrations

The initial revision `0001_initial` creates all 19 tables from the supplied schema. Only the User ORM model is implemented because authentication needs it now. Domain ORM models and repositories are Phase 1 work. Automatic migration generation is deliberately guarded until ORM coverage is complete; partial metadata could otherwise propose dropping valid tables.

```bash
docker compose run --rm migrate alembic current
docker compose run --rm migrate alembic upgrade head
```

Historical migration defaults are frozen. Changes to configurable runtime policy require `core/config.py` and `CONFIGURATION.md` to change together; a database default change also requires a new Alembic revision.

## Stop and troubleshoot

`docker compose down` stops services while retaining the named PostgreSQL volume. `docker compose down -v` permanently deletes this local database; use it only when intentionally resetting disposable demo data.

| Symptom | Resolution |
|---|---|
| `.env` already exists | Generator intentionally leaves it unchanged; review it manually |
| Database password changed but login fails | Initialization scripts run only on a new volume; existing database roles retain old passwords |
| Port already in use | Stop the conflicting local process or update Compose ports and matching API/CORS configuration |
| Dashboard redirects to login after refresh | Expected in-memory session behavior; account is still stored |
| Repeated login attempts return 429 | Wait 60 seconds; limiter is per client IP across auth routes |
| Backend readiness returns 503 | Check migration exit status and database connectivity |
| CORS error | Use `localhost` consistently, or add the exact alternate origin to `CORS_ORIGINS` |
| API URL changed but browser uses old host | Rebuild frontend; `NEXT_PUBLIC_API_URL` is embedded at build time |
| Seed, financial or chat routes are missing | Expected: they are outside Phase 0 |
