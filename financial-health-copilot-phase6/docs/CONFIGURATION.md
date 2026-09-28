# Configuration Reference

Multiple documents (`FORECASTING_AND_RISK.md`, `CONFIDENCE_AND_EXPLAINABILITY.md`, `RECOMMENDATION_ENGINE.md`, `FINANCIAL_ANALYTICS.md`) reference "configurable" thresholds. This document is the single source of truth for every tunable value in the system, so implementation matches `core/config.py` exactly and no default is reinvented differently in two places.

## Why This Exists

Scattering magic numbers across modules is exactly the kind of hidden decision-making the project brief asked us to avoid making implicitly. Every threshold below should be a named constant, loaded once, and referenced — never hardcoded inline in a second location.

## User-Level Preferences (stored per user, overridable)

| Setting | Default | Used by |
|---|---|---|
| `preferred_buffer_days` | 7 | Affordability checks, low-buffer risk |
| `currency` | INR | All display formatting |
| `forecast_horizon_default_days` | 30 | `/cash-flow/forecast` default |

## Risk Detection Thresholds

| Threshold | Default | Rule |
|---|---|---|
| `LOW_BUFFER_DAYS_HIGH` | 2 | Buffer below this → High severity |
| `LOW_BUFFER_DAYS_MEDIUM` | 5 | Buffer below this (and above High threshold) → Medium severity |
| `SPENDING_SPIKE_PCT` | 30% | Category spend vs. trailing 3-period average to flag "unusually high" |
| `RECURRING_BURDEN_PCT` | 50% | Recurring obligations as % of income to flag burden risk |
| `DEBT_SERVICE_RATIO_HIGH` | 40% | Debt service ratio to flag debt pressure |
| `CREDIT_UTILIZATION_HIGH` | 70% | Aggregate credit utilization to flag debt pressure |
| `INCOME_CV_HIGH` | 0.30 | Income coefficient of variation to flag volatility |
| `UNUSUAL_TXN_MULTIPLIER` | 3.0x | Single transaction vs. category average transaction size |
| `MIN_PERIODS_FOR_VOLATILITY` | 3 | Minimum periods of income/spend history before volatility risk can fire at all |

## Recurring Detection Tolerances

| Threshold | Default |
|---|---|
| `RECURRING_AMOUNT_TOLERANCE_PCT` | 10% |
| `RECURRING_INTERVAL_TOLERANCE_DAYS_MONTHLY` | 3 days |
| `RECURRING_INTERVAL_TOLERANCE_DAYS_WEEKLY` | 3 days |
| `RECURRING_INTERVAL_TOLERANCE_DAYS_YEARLY` | 7 days |
| `RECURRING_MIN_CONFIRMED_CYCLES` | 2 |

## Forecasting

| Threshold | Default |
|---|---|
| `FORECAST_HORIZON_MAX_DAYS` | 90 (180 for simulation) |
| `FORECAST_TREND_CAP_PCT` | ±15% |
| `FORECAST_CONFIDENCE_HIGH_MIN_MONTHS_HISTORY` | 3 |
| `FORECAST_CONFIDENCE_HIGH_MAX_SPENDING_CV` | 0.15 |
| `FORECAST_CONFIDENCE_MEDIUM_MAX_SPENDING_CV` | 0.35 |
| `FORECAST_CONFIDENCE_HIGH_MIN_RECURRING_COVERAGE_PCT` | 80% |

## Confidence Scoring Weights

| Component | Weight |
|---|---|
| `WEIGHT_DATA_COMPLETENESS` | 0.30 |
| `WEIGHT_DATA_FRESHNESS` | 0.20 |
| `WEIGHT_HISTORICAL_CONSISTENCY` | 0.20 |
| `WEIGHT_FORECAST_UNCERTAINTY` | 0.20 |
| `WEIGHT_OBSERVATION_COUNT` | 0.10 |
| `OBSERVATION_COUNT_CAP_PERIODS` | 6 |

| Confidence band | Score range |
|---|---|
| High | ≥ 0.70 |
| Medium | 0.40 – 0.69 |
| Low | 0.25 – 0.39 |
| Insufficient data (suppress) | < 0.25 |

## Recommendation Engine

| Threshold | Default |
|---|---|
| `MIN_RECOMMENDATION_CONFIDENCE` | 0.40 (below this, suppress rather than show) |
| `MIN_HISTORY_CYCLES_FOR_RECOMMENDATION` | 2 |
| `PRIORITY_SCORE_P0_MIN` | 2.0 |
| `PRIORITY_SCORE_P1_MIN` | 1.0 |
| `SEVERITY_WEIGHT_HIGH` | 3 |
| `SEVERITY_WEIGHT_MEDIUM` | 2 |
| `SEVERITY_WEIGHT_LOW` | 1 |

## Display / Rounding Rules

| Amount range | Rounding (predictions only; facts show exact) |
|---|---|
| < ₹1,000 | Nearest ₹10 |
| ₹1,000 – ₹100,000 | Nearest ₹100 |
| > ₹100,000 | Nearest ₹1,000 |

## Configuration Change Process

Any change to a value in this table during implementation must be reflected here in the same PR — this file is the reviewable diff surface for "did we just silently change what counts as a risk," which matters for both testing (`TESTING_STRATEGY.md` fixtures assume these defaults) and demo consistency.
