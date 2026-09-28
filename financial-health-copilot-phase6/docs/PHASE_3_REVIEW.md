# Phase 3 Implementation Review

## Scope completed

Phase 3 is implemented on top of the corrected Phase 2 repository. No Phase 2
analytics behavior or fixtures were replaced.

- Recurring detection groups debit transactions by merchant and the configured
  ±10% amount tolerance, then checks weekly, monthly, and yearly interval tolerances.
- One-cycle fixed expenses may be stored as candidates; patterns with at least two
  qualifying cycles are confirmed.
- Calendar-aware recurrence avoids the drift caused by treating every month as 30 days.
- `GET /api/v1/recurring-expenses` returns the detected/persisted patterns.
- `GET /api/v1/cash-flow/forecast` returns 1–90 daily chart points.
- Forecast arithmetic follows `FORECASTING_AND_RISK.md`:
  `previous balance + scheduled inflows - scheduled outflows - unscheduled spend`.
- Unscheduled spend uses up to 90 days of variable/discretionary history, excludes
  transactions already identified as recurring, and applies a trend multiplier capped
  at ±15%.
- Confidence bounds widen with spending volatility and elapsed days.
- Confidence labels use actual history length, spending CV, and recurring coverage.
- Each successful forecast is appended to `cash_flow_forecasts`.
- Recurring detection is refreshed when recurring or forecast data is requested. The
  Phase 2 ingestion contract remains unchanged; its `recalculation_triggered` flag is
  the integration hook used by later phases.

## Correctness decisions

- The latest ingested transaction date is the deterministic `as_of_date`. This keeps
  seeded demos and automated tests reproducible instead of depending on the computer's date.
- Irregular income is not guessed. Only income sources with a supported recurrence are scheduled.
- Loan installments are scheduled from structured loan records; debt-payment transactions
  are excluded from generic recurring detection to prevent double-counting.
- Scheduled flows and unscheduled spend are both applied on the same day.
- All monetary calculations use `Decimal`.

## Verification

- Backend result: 66 passed; 2 PostgreSQL-gated checks are skipped unless
  `TEST_DATABASE_URL` is supplied.
- Corrected Phase 2 regression suite remains green.
- Forecast fixtures cover Ananya, Rohit and Meera, including three exact chart points each.
- The required truncated-history confidence behavior is table-tested.
- Tests cover calendar month ends, confidence boundaries, double-count prevention,
  API validation, no-data handling, recurring detection and persistence.
- PostgreSQL-only migration tests remain gated by `TEST_DATABASE_URL` and run in Docker/CI.

## Phase boundary

Risk detection, recommendations, impact simulation and AI chat remain Phases 4–5.
The Phase 6 frontend will visualize the forecast; Phase 3 exposes the chart-ready API data.
