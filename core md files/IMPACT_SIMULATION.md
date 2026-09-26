# Impact Simulation

This is the engine that answers **"What happens if I do this?"** — the feature that most distinguishes this product from a dashboard.

## Design Principle

Every simulation compares two projections computed with the **exact same forecasting logic** (`FORECASTING_AND_RISK.md`), differing only in the input assumptions:

- **Baseline scenario:** the current forecast, unmodified.
- **Proposed scenario:** the same forecast, with one input changed according to the requested action.

Both projections must use the same engine so the comparison is apples-to-apples and every number in the diff is traceable to a change in a single, named input.

## Supported Action Types (MVP)

| Action type | Parameters | What changes in the projection |
|---|---|---|
| `reduce_spending` | category, amount, period | Rolling-average unscheduled spend for that category reduced by `amount` for the simulated period |
| `increase_savings` | amount, period | A scheduled outflow to a savings "bucket" of `amount` is added; balance projection reduced accordingly but tracked separately as `savings_delta` |
| `extra_debt_payment` | loan_id, amount, date | Loan amortization re-run with an additional principal payment of `amount` on `date`; cash balance projection reduced by `amount` on that date |
| `delay_purchase` | amount, original_date, new_date | A planned one-off expense of `amount` is removed from `original_date` and re-scheduled at `new_date` |
| `modify_recurring` | recurring_id, new_amount OR cancel: true | The recurring schedule's `expected_amount` is changed (or the item removed) for all future occurrences in the simulated window |
| `change_income` | amount OR percent, effective_date | Scheduled income inflows adjusted from `effective_date` forward |

## Output Structure

```json
{
  "action": { "type": "extra_debt_payment", "loan_id": "...", "amount": 10000, "date": "2026-10-05" },
  "baseline": {
    "projected_balance_series": [...],
    "loan_payoff_months": 14,
    "total_interest_remaining": 8200,
    "cash_buffer_days_min": 9
  },
  "proposed": {
    "projected_balance_series": [...],
    "loan_payoff_months": 11,
    "total_interest_remaining": 6100,
    "cash_buffer_days_min": 5
  },
  "delta": {
    "loan_payoff_months": -3,
    "total_interest_remaining": -2100,
    "cash_buffer_days_min": -4
  },
  "confidence": "medium",
  "trade_off_note": "Cash buffer decreases from 9 to 5 days immediately after the extra payment."
}
```

## Comparison Dimensions

Every simulation reports, wherever applicable to the action type:
- Projected balance (full series + month-end)
- Savings accumulated
- Debt balance and payoff timeline
- Cash buffer (minimum over the simulated window, not just end value — a mid-month dip matters even if it recovers)
- Debt payoff timeline
- Affordability status changes
- Risk indicator changes (does this action resolve, worsen, or newly trigger a risk?)

## What Is Deterministic

**Everything.** The entire simulation — re-running the rolling-average/schedule forecast with modified inputs, amortization recalculation, ratio recalculation — is deterministic Python. The LLM's only role is to (a) parse the user's natural-language what-if into a structured `action` object (e.g., "what if I cancel Netflix" → `{type: modify_recurring, recurring_id: <netflix>, cancel: true}`) and (b) narrate the resulting JSON in plain language. The LLM never computes the `baseline`/`proposed`/`delta` numbers.

## Pseudocode

```python
def simulate_action(user_id: str, action: Action) -> SimulationResult:
    current_state = load_financial_state(user_id)

    baseline_forecast = run_forecast(current_state, horizon_days=90)

    modified_state = apply_action(current_state, action)  # pure function, returns a new state
    proposed_forecast = run_forecast(modified_state, horizon_days=90)

    delta = compute_delta(baseline_forecast, proposed_forecast)
    confidence = min(baseline_forecast.confidence, proposed_forecast.confidence)

    return SimulationResult(
        action=action,
        baseline=summarize(baseline_forecast),
        proposed=summarize(proposed_forecast),
        delta=delta,
        confidence=confidence,
        trade_off_note=generate_trade_off_note(delta),  # simple rule-based sentence, not LLM
    )


def apply_action(state: FinancialState, action: Action) -> FinancialState:
    new_state = state.copy()
    if action.type == "reduce_spending":
        new_state.category_rolling_avg[action.category] -= action.amount
    elif action.type == "extra_debt_payment":
        new_state.loans[action.loan_id] = amortize_with_extra_payment(
            state.loans[action.loan_id], action.amount, action.date
        )
        new_state.scheduled_outflows.append((action.date, action.amount))
    elif action.type == "delay_purchase":
        new_state.scheduled_outflows.remove((action.original_date, action.amount))
        new_state.scheduled_outflows.append((action.new_date, action.amount))
    elif action.type == "modify_recurring":
        if action.cancel:
            new_state.recurring.remove(action.recurring_id)
        else:
            new_state.recurring[action.recurring_id].amount = action.new_amount
    elif action.type == "change_income":
        new_state.income_sources = adjust_income(state.income_sources, action)
    elif action.type == "increase_savings":
        new_state.scheduled_outflows.append(("savings_bucket", action.amount))
    return new_state
```

## Validation Rules

- `reduce_spending.amount` cannot exceed the category's current period total (can't reduce below ₹0).
- `extra_debt_payment.amount` cannot exceed `loan.outstanding_balance`.
- `delay_purchase.original_date` must correspond to an actual scheduled/recent transaction or user-declared planned purchase.
- All simulations run over a bounded horizon (default 90 days, max 180) to keep confidence meaningful.

## Worked Examples (from the problem statement)

1. **"Reduce food delivery spending by ₹3,000/month"** → `reduce_spending(category=Dining, amount=3000)` → buffer improves, month-end balance improves by ~₹3,000.
2. **"Save ₹5,000 more every month"** → `increase_savings(amount=5000)` → savings trajectory rises, buffer may tighten short-term depending on how the ₹5,000 is sourced (surfaced as a trade-off note).
3. **"Pay ₹10,000 extra toward loan"** → `extra_debt_payment` → payoff timeline shortens, interest drops, immediate buffer dips (see JSON example above).
4. **"Income drops by 10%"** → `change_income(percent=-10)` → all downstream forecasts and risk checks re-evaluated against reduced income; likely surfaces new/worsened risks.
5. **"Buy a ₹50,000 phone next month"** → treated as `delay_purchase` with `original_date = None` (a hypothetical new one-off expense) inserted into the schedule; compared against baseline to show affordability and buffer impact.
6. **"Cancel this subscription"** → `modify_recurring(cancel=true)` → recurring burden and buffer both improve; shown explicitly.
