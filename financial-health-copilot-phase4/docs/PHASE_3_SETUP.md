# Phase 3 Setup and Verification (Windows + Docker)

## 1. Extract safely

Extract the corrected ZIP into a new folder. Do not overwrite the older Phase 2 folder
until Phase 3 has passed verification on your computer.

Copy your existing `.env` into the new repository root. If you do not have `.env`, open
PowerShell in the repository root and run:

```powershell
python scripts/setup_env.py
```

## 2. Start the stack

Start Docker Desktop, wait until it reports that Docker is running, and then run:

```powershell
docker compose up --build -d
docker compose ps
```

Wait until `db`, `backend`, and `frontend` are healthy. Do not add `-v` to
`docker compose down`, because `-v` deletes the PostgreSQL volume.

## 3. Run verification

```powershell
docker compose exec backend pytest -q
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
```

To include the PostgreSQL-gated migration checks:

```powershell
docker compose exec backend sh -c 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q'
```

## 4. Seed the personas

```powershell
docker compose exec backend python scripts/seed_demo_data.py --persona all
```

The command is safe to repeat; duplicate transactions are skipped.

## 5. Inspect Phase 3

Open `http://localhost:8000/docs` and log in with one of the demo accounts, such as:

- Email: `ananya.demo@example.com`
- Password: `demo-passphrase-2026`

Use the returned token with the **Authorize** button, then call:

1. `GET /api/v1/recurring-expenses`
2. `GET /api/v1/cash-flow/forecast?horizon_days=30`

The normal frontend does not show the forecast chart yet; that page belongs to Phase 6.

## 6. Stop when finished

```powershell
docker compose down
```
