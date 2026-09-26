# Backend Architecture

## Module Layout (modular monolith, single FastAPI app)

```
backend/
├── app/
│   ├── main.py
│   ├── auth/            # signup, login, JWT
│   ├── users/
│   ├── accounts/
│   ├── transactions/    # ingestion, dedup, manual corrections
│   ├── categorization/  # merchant normalization, rules, recurring detection
│   ├── analytics/       # FINANCIAL_ANALYTICS.md formulas
│   ├── forecasting/     # rolling-average + schedule forecast
│   ├── risk/            # rule engine
│   ├── recommendations/ # generation, ranking, dedup
│   ├── simulation/      # what-if engine
│   ├── agent/           # LLM orchestration, tool registry
│   ├── chat/            # sessions/messages persistence
│   ├── core/            # config, db session, security utils, shared schemas
│   └── db/              # SQLAlchemy models, migrations (Alembic)
├── tests/
└── requirements.txt
```

## Service Boundaries

Each module exposes a small set of pure-ish functions (a "service" object or module-level functions) that other modules call directly (in-process function calls — no internal HTTP), e.g.:

```python
# forecasting/service.py
def get_forecast(user_id: UUID, horizon_days: int = 30) -> ForecastResult: ...

# risk/service.py
def evaluate_risks(user_id: UUID) -> list[RiskEvent]:
    forecast = forecasting.get_forecast(user_id)
    summary = analytics.get_summary(user_id)
    ...
```

This keeps the system testable (each service mockable/unit-testable in isolation) without the overhead of network boundaries between modules.

## Repositories

Each module with persistence has a thin repository layer (`transactions/repository.py`, `recommendations/repository.py`, etc.) wrapping SQLAlchemy queries — keeps business logic (in `service.py`) free of raw SQL/ORM details and easy to unit test with a fake repository.

## Business Logic Placement

- **Analytics/forecasting/risk/recommendation/simulation:** pure business logic modules, no FastAPI dependency — importable and testable standalone (critical since these are the modules with the strictest correctness requirements).
- **API routers (`*/router.py`):** thin — parse request, call service, shape response, handle HTTP-level errors only.

## Validation

- Pydantic models define every request/response schema; FastAPI enforces these automatically at the boundary.
- Domain-level validation (e.g., "extra payment can't exceed outstanding balance") lives in the relevant service function and raises typed domain exceptions (`InvalidSimulationError`, `InsufficientDataError`) that a shared exception handler maps to HTTP error responses.

## Background Jobs

- MVP: `recalculate_user(user_id)` is triggered synchronously and inline after any data-mutating request (`POST /transactions`, `PATCH /transactions/{id}`, loan/income changes) — acceptable given hackathon data volumes (recalculation completes in well under 2s).
- If needed for demo smoothness, this can be moved to a FastAPI `BackgroundTasks` call so the mutating request returns immediately and the frontend polls/refetches — documented as the first upgrade path, not required for MVP.

## Caching

- Not required at hackathon scale. If added: cache `get_financial_summary`/`get_cash_flow_forecast` per user with invalidation on `recalculate_user` — a simple in-process dict or `functools.lru_cache`-style keyed cache is sufficient; no Redis needed for this scope.

## Error Handling

- Centralized FastAPI exception handlers map domain exceptions to the standard error envelope (`{"error": {"code","message","details"}}`).
- `InsufficientDataError` → `404` with a `code` the frontend recognizes to render `<InsufficientDataCard>` rather than a generic error.
- LLM/agent failures never surface as raw 500s — the agent module catches provider errors and returns a templated degraded response (`503` with a clear, user-facing message), while all deterministic endpoints remain unaffected.

## Configuration

- All thresholds (buffer days default, risk thresholds, forecast horizon defaults, confidence weight coefficients) live in `core/config.py` as named constants — single source of truth referenced by `risk`, `forecasting`, and `recommendations` modules, not duplicated.
