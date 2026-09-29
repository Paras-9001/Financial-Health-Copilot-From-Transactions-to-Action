# Phase 4 Implementation Review

## Scope completed

- Seven deterministic risk rules run from the latest transaction date and persist
  active/resolved lifecycle state.
- Existing risks are refreshed in place when their evidence, confidence, or severity changes.
- Recommendations are evidence-backed, confidence-filtered, deduplicated, and ranked with
  the documented severity × confidence × normalized-impact formula.
- Repeated reads retain stable recommendation IDs; removed actions are marked superseded.
- Every recommendation impact is recalculated by the canonical simulation/forecast engine.
- All six MVP simulation actions are supported, including credit-card or loan extra payments.
- Simulations compare full baseline and proposed series over a configurable 1–180-day horizon.
- Cash buffer is reported in days, independently from minimum projected cash balance.
- Affordability uses the simulated minimum balance and preferred buffer.
- Scenario 7 is reproducible with transaction ingestion followed by risk and recommendation calls.

## Correctness decisions

- The newest transaction date remains the deterministic `as_of_date`.
- Spending reductions are validated against the matching category's most recent 30-day total.
- A hypothetical purchase (`original_date` omitted) is added only to the proposed scenario.
  A delayed planned purchase appears at its original date in the baseline and new date in the proposal.
- Income changes begin on `effective_date`, or the day after `as_of_date` when omitted.
- Extra debt payments reduce principal/card balance and also create the corresponding cash outflow.
- Loan payoff and remaining interest use deterministic monthly amortization, not balance/installment division.
- Monetary calculations use `Decimal`; invalid or infeasible recommendation candidates are suppressed.

## Persistence and migration

Migration `0003_phase4` adds the required `recommendations.expected_impact` JSONB column.
The readiness endpoint requires Alembic head `0003_phase4`.

## Verification

- `104 passed`, `2 skipped` (the skipped checks require a live PostgreSQL test database).
- Ruff lint and format checks pass.
- Alembic offline replay reaches `0003_phase4` successfully.
- Tests assert real forecast deltas for reduced spending, lower income, increased savings,
  hypothetical purchases, stable recommendation IDs, input validation, and Scenario 7 recalculation.

## Phase boundary

Phase 5 AI orchestration/chat and Phase 6 frontend pages are intentionally not included.
