# Phase 1 setup and verification

## Upgrade from Phase 0

Keep the existing root `.env` and database volume. From the repository root:

```bash
docker compose up --build -d
docker compose ps -a
```

The one-shot `migrate` service applies `0002_phase1`. It should exit with code 0; the other three services should become healthy. `/ready` now requires database revision `0002_phase1`.

## Verify

```bash
docker compose exec backend pytest -q
docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q'
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
```

The image directs Ruff's cache to `/tmp`, so checks work under the non-root runtime user.

## Seed personas and prove idempotency

```bash
docker compose exec backend python scripts/seed_demo_data.py --persona all
docker compose exec backend python scripts/seed_demo_data.py --persona all
```

The first run inserts synthetic records. The second must insert zero transactions and report duplicates skipped. The three local development accounts share the default password `demo-passphrase-2026`; set `DEMO_USER_PASSWORD` in the backend environment before seeding if you want another password.

## CSV and manual onboarding

Create a normal account in the frontend, open `http://localhost:8000/docs`, click **Authorize**, and paste the JWT returned by signup/login. The template is `data/seed/transactions-template.csv`.

- CSV: `/imports/csv/preview`, then `/imports/csv/confirm`.
- Manual: create an account first, then income, loan/card details, and transactions.
- Demo: list `/onboarding/personas`, then call `/onboarding/demo` once for an empty account.

Financial calculations are intentionally not present yet. `recalculation_triggered` records that new data entered the recalculation boundary; Phase 2 supplies the analytics implementation behind that boundary.
