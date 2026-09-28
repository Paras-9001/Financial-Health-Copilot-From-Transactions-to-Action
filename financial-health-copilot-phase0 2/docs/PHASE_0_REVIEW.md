# Phase 0 review

Reviewed: 27 September 2026. Scope: Phase 0 only in the supplied `IMPLEMENTATION_PLAN.md`.

**Result: Phase 0 is implemented and its application components have been exercised. Native Docker Compose acceptance remains unverified in this workspace because Docker is unavailable.** The included CI workflow and local setup commands provide that remaining check. No Phase 1–9 financial functionality is claimed complete.

## Acceptance criteria and evidence

| Required item | Implementation | Verification result |
|---|---|---|
| Frontend/backend/Compose scaffold | Next.js, FastAPI, PostgreSQL, one-shot migration service | Frontend production build passes; standalone server and API started for browser checks; Compose YAML parsed and startup dependencies reviewed |
| Schema migration | Alembic `0001_initial` plus Phase 5 `0002_chat_schema`, all 19 documented tables, money columns, FKs and indexes | Upgrade → downgrade → upgrade passed on PGlite's embedded PostgreSQL engine through psycopg/Alembic |
| Signup and login | Email normalization, bcrypt password hash, JWT issuance, protected current-user route | Unit/integration checks and a real browser flow pass |
| Empty dashboard | Authenticated responsive overview with explicit absence of financial data | Browser check passes; desktop 1440px and mobile 390px screenshots inspected; no horizontal overflow |
| Central configuration | All 36 named document settings plus unnamed confidence/rounding values | Document-parity test, weight/band checks and consumer redefinition guard pass |
| CI lint/test hook | GitHub Actions with lint, types, Compose build, PostgreSQL tests, browser tests and migration round trip | Workflow reviewed and YAML parsed; not executed on GitHub in this task |
| `docker compose up` starts all services | Health-gated startup and dedicated migration identity | **Pending native Docker execution**, not represented as a completed check |

## Checks actually run

- Backend: **19 auth/config tests passed**, with the two PostgreSQL-specific tests skipped in the isolated SQLite run.
- Embedded PostgreSQL run: **20 tests passed**, including schema/table/precision inspection. One savepoint-based test was excluded after the PGlite socket bridge failed to recover from an intentionally rejected FK insert. That same owner constraint and delete cascade were checked successfully through PGlite's direct SQL API. The original PostgreSQL test remains in the project and is included in native CI.
- Migration: initial creation, rollback to base and reapplication passed through Alembic and the PostgreSQL driver against PGlite.
- Backend Ruff lint and formatting checks passed; `pip check` found no broken dependency requirements.
- Frontend ESLint, TypeScript and production build passed.
- Both committed Playwright browser tests passed against the real FastAPI app and migrated embedded database. They ran in separate browser processes because this environment's headless Chromium build does not reliably reuse contexts. The delivered normal Playwright configuration does not require those environment-specific workarounds.
- Browser flow covered signup → protected empty dashboard → logout → incorrect password error → successful login → refresh returns to login, plus direct unauthenticated dashboard redirect.
- Frontend production dependency audit reported **0 known vulnerabilities at review time**. This is a point-in-time package audit, not a security certification or a Python vulnerability audit.
- All **38 supplied Markdown files** inside `core md files/` were compared byte-for-byte and preserved under `docs/`. The original project README is preserved separately.

PGlite is a PostgreSQL engine compiled for an embedded runtime; it is useful evidence for SQL and application behavior, but it does not verify the native PostgreSQL container, bootstrap roles, Docker networking or container health ordering. Those remain a distinct local/CI acceptance gate.

## Findings fixed during review

1. **Configuration test omitted numeric names.** The parser now includes digits, so `PRIORITY_SCORE_P0_MIN` and `PRIORITY_SCORE_P1_MIN` are both covered; all 36 named entries are compared.
2. **Container test could not see its reference document.** The backend image now copies `CONFIGURATION.md` into the correct path without including the entire repository.
3. **Frontend lint violations.** Navigation uses Next.js `Link`; configuration exports meet lint rules.
4. **Browser error assertion matched the route announcer.** The test now identifies the actual incorrect-password alert, rather than assuming there is only one alert on a Next.js page.
5. **Potential unsafe migration autogeneration with partial ORM coverage.** A guard rejects `--autogenerate` until the remaining domain models exist. Historical schema is not inferred from the User-only metadata.
6. **Validation errors could expose submitted secrets if default details were returned.** Error handlers return field names and messages without raw input values.

7. **Clean-checkout route types.** The typecheck script generates Next.js route types before running TypeScript, so CI does not depend on a previous local build.

## Known limits of this phase

| Item | Status and impact |
|---|---|
| Native Docker execution | Must be checked with the included commands or CI before treating Phase 0 deployment acceptance as fully green |
| Browser session | Token is memory-only; refresh logs out. This is intentional and explained in the UI |
| Logout revocation | Browser token is cleared; a copied bearer token remains valid for up to 30 minutes. Server-side revocation/refresh sessions are future work |
| Auth rate limit | Single-process memory, per client IP. Not a distributed or production-grade rate limiter |
| Identity | No email verification, password recovery or MFA; use synthetic demo accounts |
| Database security | Runtime role is designed without DDL/superuser access. Native bootstrap/grants still need the Docker check; row-level security is outside the supplied MVP scope |
| Test tooling | A Starlette warning deprecates its current httpx TestClient adapter; pinned tests still pass. Upgrade the adapter when updating the test stack |
| Readiness version | `/ready` now expects `0002_chat_schema`; update it when a later phase adds a revision |
| Production operation | Local HTTP, no managed TLS, no production backup/restore rehearsal, no public deployment |

## Schema questions to settle before Phase 1 ingestion

These are inherited design ambiguities, not implemented financial behavior:

- The supplied transaction schema permits signed nonzero amounts while also storing debit/credit direction. Define one canonical sign convention before accepting financial records.
- The planned hash `(account, date, amount, description)` can collapse two legitimate identical purchases. Preserve source IDs or reviewed duplicate handling before claiming robust import deduplication.
- Account balances default to zero without an explicit as-of timestamp. Decide how missing balances and dated anchors will be represented before producing forecasts.
- Accounts and loan/card extension tables repeat outstanding values. Define which value is authoritative and how updates stay consistent.
- Some cross-entity ownership checks will still be repository responsibilities; do not assume all future tenant isolation is enforced by existing FKs.

These matters are recorded for Phase 1 without silently redesigning the provided project schema in Phase 0.

## Local reviewer checklist

```bash
python3 scripts/setup_env.py
docker compose up --build
```

In a second terminal:

```bash
docker compose ps
docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q'
```

Then open `http://localhost:3000`, create a demo account, inspect the empty dashboard, log out and log back in. Confirm `http://localhost:8000/ready` returns `{"status":"ready"}`. These checks resolve the principal remaining environment limitation.

## Included review images

The ZIP contains `docs/review-images/login-desktop.png`, `dashboard-desktop.png` and `dashboard-mobile.png`. They are captures of the implemented app, not design mockups.
