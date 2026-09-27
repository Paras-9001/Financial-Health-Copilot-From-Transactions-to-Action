# Financial Health Copilot — Phase 4

**From Transactions to Action.** Phase 4 adds the **Recommendation Engine** on top of the Phase 3 forecasting foundation:

- **Risk Rule Engine** — 7 deterministic rules from `FORECASTING_AND_RISK.md` (`low_cash_buffer`, `upcoming_cash_flow_gap`, `unusually_high_spending`, `recurring_payment_burden`, `debt_pressure`, `income_volatility`, `unusual_transaction`). Risks are persisted and resolved when conditions no longer hold.
- **Recommendation Generation** — risk-type-specific candidate templates, parameterized from evidence, run through the impact simulation engine for `expected_impact`. Ranked by `severity_weight × confidence × normalized_impact`. Filtered at confidence ≥ 0.40. Deduplicated by `risk_event_id + action.type`.
- **Impact Simulation Engine** — 6 action types (`reduce_spending`, `increase_savings`, `extra_debt_payment`, `delay_purchase`, `modify_recurring`, `change_income`). Each simulation runs the same deterministic forecast on baseline and modified state, returns `baseline / proposed / delta / trade_off_note`. Fully deterministic — no LLM.
- **New API endpoints**: `GET /risks`, `GET /recommendations`, `GET /recommendations/{id}/history`, `POST /simulate`, `POST /affordability/check`.

**Phases 0–4 are implemented.** AI chat (Phase 5) and frontend (Phase 6) remain later phases. All APIs are exercisable through `/docs`.

## Start locally

Prerequisites: Docker Desktop with Docker Compose v2, and Python 3 to generate the local environment file.

```bash
cd financial-health-copilot-phase4
python scripts/setup_env.py
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000) for the dashboard, [http://localhost:8000/docs](http://localhost:8000/docs) for the API.

- API liveness: `http://localhost:8000/health` (reports `{"status": "ok", "phase": 4}`)
- Migration readiness: `http://localhost:8000/ready`

## Phase 4 quick verification

```bash
docker compose exec backend pytest -q
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
```

Seed demo data and exercise all Phase 4 endpoints:

```bash
docker compose exec backend python scripts/seed_demo_data.py --persona all
```

Log in as `ananya.demo@example.com` (password `demo-passphrase-2026`) and call:

- `GET /api/v1/risks` — returns active risk events with evidence and confidence
- `GET /api/v1/recommendations` — returns ranked, evidence-backed action recommendations
- `POST /api/v1/simulate` — what-if simulation (see examples below)
- `POST /api/v1/affordability/check` — can I afford a large purchase?

### Simulation examples

```bash
# Reduce dining by ₹2,500
curl -X POST http://localhost:8000/api/v1/simulate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"action_type": "reduce_spending", "params": {"category": "Dining", "amount": "2500"}}'

# Pay ₹10,000 extra on loan
curl -X POST http://localhost:8000/api/v1/simulate \
  -H "Authorization: Bearer <token>" \
  -d '{"action_type": "extra_debt_payment", "params": {"loan_id": "<uuid>", "amount": "10000", "date": "2026-10-05"}}'

# What if income drops 10%?
curl -X POST http://localhost:8000/api/v1/simulate \
  -H "Authorization: Bearer <token>" \
  -d '{"action_type": "change_income", "params": {"percent": "-10"}}'

# Affordability check
curl -X POST http://localhost:8000/api/v1/affordability/check \
  -H "Authorization: Bearer <token>" \
  -d '{"amount": "180000.00", "target_date": "2026-11-15"}'
```

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
| Recurring Expenses | `GET /api/v1/recurring-expenses` |
| Forecasting | `GET /api/v1/cash-flow/forecast` |
| **Risk Events** | **`GET /api/v1/risks`** |
| **Recommendations** | **`GET /api/v1/recommendations`, `GET /api/v1/recommendations/{id}/history`** |
| **Simulation** | **`POST /api/v1/simulate`, `POST /api/v1/affordability/check`** |
| Operations | `/health`, `/ready` |

## Project layout

| Path | Purpose |
|---|---|
| `backend/app/risks/` | 7-rule risk engine, persistence (resolved-not-deleted), API router |
| `backend/app/recommendations/` | Candidate generation, canonical impact simulation, ranking/dedup pipeline |
| `backend/app/simulation/` | Deterministic what-if engine, apply_action, affordability check |
| `backend/app/analytics/` | Deterministic financial analytics functions, schemas, repository |
| `backend/app/recurring/` | Recurring-pattern detection and persistence |
| `backend/app/forecast/` | Rolling-average + schedule forecast |
| `backend/app/core/` | Configuration (all thresholds from `CONFIGURATION.md`), database, security |
| `backend/app/db/` | ORM models including `RiskEvent`, `Recommendation`, `RecommendationImpact` |
| `backend/tests/test_phase4.py` | Risk rules unit tests, persona integration tests, simulation tests, Scenario 7 |
| `docs/` | Architecture documentation |

See `docs/PHASE_4_REVIEW.md`, `docs/PHASE_4_API.md`, and
`docs/PHASE_4_SETUP.md` for the implementation decisions, request examples, and
Docker/PostgreSQL verification steps.
