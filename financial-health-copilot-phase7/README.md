# Financial Health Copilot — Phase 7

Phase 7 completes the real frontend/backend integration specified by the authoritative documents in `core md files/`. New financial data now updates account state, reruns the deterministic analysis, refreshes every dependent view, and explains the before/after change through the shared recalculation toast.

**Phases 0–7 are implemented cumulatively.** The full application can now be tested from signup through onboarding, analysis, recommendations, simulations, chat, and live recalculation using only the UI.

## Frontend routes

| Route | Experience |
|---|---|
| `/login` | Login and signup |
| `/onboarding` | Demo persona, CSV import, and manual entry |
| `/` | Core-loop dashboard: observed → predicted → recommended → impact |
| `/transactions` | Search, add, and manually categorize transactions |
| `/spending` | Category breakdown and accessible chart |
| `/cash-flow` | Forecast, confidence band, recurring payments, and risks |
| `/debt` | Debt metrics, loans, cards, and simulator entry points |
| `/recommendations` | Ranked actions, evidence, expected impact, and history |
| `/simulate` | Six deterministic what-if action types |
| `/chat` | Grounded Copilot with inline labeled claims |

## Run locally

```bash
cd financial-health-copilot-phase7
python scripts/setup_env.py
docker compose up --build
```

Open `http://localhost:3000`. New accounts are taken directly to onboarding. “Explore with sample data” is the fastest full-product path.

## Verify

```bash
docker compose exec backend pytest -q
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run lint
docker compose exec frontend npm run build
```

With the stack running:

```bash
cd frontend
npm run test:e2e
```

## Phase 7 acceptance flow

1. Sign up and choose the Ananya sample persona.
2. Open Transactions and add a ₹12,000 debit dated 2026-09-28 with description `UNPLANNED MEDICAL EXPENSE`.
3. Select **Save and recalculate**.
4. Verify the toast shows the changed expenses, buffer/risk, and recommendation, then follow **See what changed**.

Phase 8 remains the dedicated test-suite expansion, and Phase 9 remains demo polish. See `docs/PHASE_7_IMPLEMENTATION.md`, `docs/PHASE_7_REVIEW.md`, and `docs/PHASE_7_SETUP.md`.
