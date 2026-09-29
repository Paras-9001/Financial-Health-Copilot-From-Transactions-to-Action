# Phase 7 Setup and User Test

## Start

```bash
cd financial-health-copilot-phase7
python3 scripts/setup_env.py
docker compose up --build
```

Open `http://localhost:3000`, create an account, and choose Ananya under sample data.

## Test live recalculation

Open Transactions, select **Add transaction**, choose Ananya Checking, and enter:

- Date: `2026-09-28`
- Amount: `12000`
- Direction: Expense
- Description: `UNPLANNED MEDICAL EXPENSE`

Select **Save and recalculate**. The toast explains the changed financial picture and links to the updated recommendations. Returning to Overview shows the refreshed summary and forecast.

## Run checks

```bash
docker compose exec backend pytest -q
docker compose exec backend ruff check app tests
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run lint
docker compose exec frontend npm run build
```

For browser tests, install Playwright Chromium once and run `npm run test:e2e` inside `frontend` while the stack is running.
