# Phase 3 API Reference

Base URL: `/api/v1`. Both endpoints require `Authorization: Bearer <JWT>`.

## `GET /recurring-expenses`

Refreshes deterministic recurring detection and returns persisted candidate/confirmed patterns.

```json
{
  "recurring": [
    {
      "id": "uuid",
      "merchant": "Netflix",
      "amount": "649.00",
      "amount_variance_pct": "0.00",
      "frequency": "monthly",
      "next_expected_date": "2026-10-19",
      "status": "confirmed",
      "confirmed_cycles": 3
    }
  ]
}
```

## `GET /cash-flow/forecast`

Query parameter: `horizon_days` (optional, default `30`, minimum `1`, maximum `90`).

```json
{
  "as_of_date": "2026-09-26",
  "horizon_days": 30,
  "daily_projection": [
    {
      "date": "2026-09-27",
      "projected_balance": "8628.41",
      "lower_bound": "8309.42",
      "upper_bound": "8947.40",
      "scheduled_inflow": "0.00",
      "scheduled_outflow": "0.00",
      "unscheduled_spend": "371.59"
    }
  ],
  "confidence": "low",
  "method": "rolling_average_v1",
  "history_days": 88,
  "spending_cv": "0.86",
  "recurring_coverage_pct": "81.98",
  "assumptions": ["..."]
}
```

The confidence can legitimately differ by persona. Low confidence does not mean the
endpoint failed; it means the documented history, volatility, or recurring-coverage
thresholds require the prediction to be presented cautiously.

Errors:

- `404 no_data`: the user has no transactions.
- `422 validation_error`: `horizon_days` is outside 1–90.
