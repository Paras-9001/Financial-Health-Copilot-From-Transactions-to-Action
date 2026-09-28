# Forecasting and Risk Detection

## Forecasting Approach: Start Simple, Interpretable

The MVP forecast is built entirely from three deterministic ingredients:

1. **Known future cash flows** — confirmed recurring payments (`next_expected_date`, `expected_amount`) and confirmed income sources. These are scheduled directly into the projection on their expected dates.
2. **Rolling-average estimate for unscheduled spend** — trailing 30/60/90-day average daily discretionary + variable spend, applied to days without a known scheduled item.
3. **Trend adjustment** — a simple linear trend over the last 3 periods' total spend, applied as a mild multiplier (capped at ±15%) to the rolling average, so a consistently rising spending pattern is reflected without overreacting to one noisy month.

`projected_balance(day) = projected_balance(day-1) + scheduled_flows(day) − rolling_avg_unscheduled_spend × trend_factor`

### Confidence Intervals

`upper_bound / lower_bound = projected_balance(day) ± (spending_cv × rolling_avg_unscheduled_spend × sqrt(days_elapsed))`

- Wider band the further out the forecast, and wider when `spending_cv` (see `FINANCIAL_ANALYTICS.md`) is high.
- Overall forecast confidence label:
  - **High** — ≥3 months of history, spending_cv < 0.15, ≥80% of expenses are scheduled/recurring.
  - **Medium** — 1–3 months history or spending_cv 0.15–0.35.
  - **Low** — <1 month history or spending_cv > 0.35, or recurring coverage <50%.

### When More Sophisticated ML Would Be Appropriate

This rolling-average + schedule approach is deliberately simple and fully explainable — appropriate for a hackathon and for a product whose core promise is transparency. Upgrading to ARIMA/Prophet/a small LSTM would be justified only when:
- There's enough per-user history (12+ months) to make a learned seasonal model outperform a rolling average.
- The rule-based forecast's error (backtested — see `EVALUATION_METRICS.md`) is demonstrably worse than a learned model's on held-out periods.
- Explainability can be preserved (e.g., via feature attribution) so predictions can still be labeled with a defensible confidence and reason.

This is documented as **Future Scope**, not MVP.

## Risk Detection Rules

Each rule below runs against the latest `financial_snapshot` + `cash_flow_forecast` on every recalculation.

| Risk | Condition | Severity | Evidence | Confidence basis |
|---|---|---|---|---|
| Low cash buffer | `cash_buffer_days < 5` (configurable) | High if <2 days, else Medium | current balance, avg daily expense | High if ≥30 days history |
| Upcoming cash-flow gap | forecast shows `projected_balance < 0` (or `< buffer_pref`) within horizon | High | date of breach, contributing scheduled flows | Forecast confidence (see above) |
| Unusually high spending | category spend this period > 130% of trailing-3-period average | Medium | category, current vs. average amount | Medium–High depending on history length |
| Recurring payment burden | `recurring_burden_pct > 50%` | Medium | list of recurring obligations and total | High (recurring data is fact-based) |
| Debt pressure | `debt_service_ratio > 40%` OR `credit_utilization > 70%` | High | ratio value, contributing accounts | High |
| Income volatility | `income_cv > 0.3` over ≥3 periods | Medium | income series, CV value | Medium (needs ≥3 periods; else suppressed) |
| Unusual transaction | single transaction > 3× category's average transaction size | Low–Medium | transaction id, amount, category average | High (fact-based, not a projection) |

### Rule Output Shape

```json
{
  "risk_type": "upcoming_cash_flow_gap",
  "severity": "high",
  "evidence": {
    "breach_date": "2026-10-14",
    "projected_balance": -1450.00,
    "contributing_flows": ["Rent -15000 on 2026-10-10", "EMI -8000 on 2026-10-12"]
  },
  "confidence": 0.72
}
```

### Resolution

A risk is marked `resolved` (not deleted) when its triggering condition no longer holds on a subsequent recalculation — e.g., income arrives and the forecast no longer shows a breach. This resolution is itself surfaced to the user ("This risk is resolved because...") to reinforce the system's adaptiveness.
