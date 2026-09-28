# Financial Health Copilot — Phase 6

Phase 6 adds the complete responsive frontend specified by the authoritative documents in `core md files/`: the shared design system, all product pages, three onboarding paths, React Query server state, and accessible financial charts.

**Phases 0–6 are implemented.** Phase 7 remains the formal end-to-end integration and recalculation-polish pass, although this frontend already calls the real Phase 1–5 APIs rather than mocks.

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
cd financial-health-copilot-phase6
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

## Phase boundary

Phase 6 delivers the complete navigable UI and wires it to the existing API contracts. Phase 7 is still responsible for formal contract-mismatch cleanup, the recommendation-change diff view, and the final `<RecalculationToast>` behavior required for the live adaptation demo.

See `docs/PHASE_6_IMPLEMENTATION.md`, `docs/PHASE_6_REVIEW.md`, and `docs/PHASE_6_SETUP.md`.
