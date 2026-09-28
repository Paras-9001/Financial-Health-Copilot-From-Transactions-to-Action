# Phase 4 API Reference

Base URL: `/api/v1`. All endpoints require `Authorization: Bearer <JWT>`.

## Risks and recommendations

- `GET /risks?status=active` reruns the risk engine and returns evidence-backed events.
- `GET /recommendations?status=active` reruns the risk/recommendation pipeline.
- `GET /recommendations/{id}/history` returns the lifecycle timeline for the action.

Use `status=all`, `active`, `resolved` (risks), or `superseded` (recommendations) as needed.

## Simulation

`POST /simulate` accepts an optional `horizon_days` from 1–180 (default 90):

```json
{
  "action_type": "reduce_spending",
  "params": {"category": "Dining", "amount": "2500.00"},
  "horizon_days": 90
}
```

Supported actions and required parameters:

| Action | Parameters |
|---|---|
| `reduce_spending` | `category`, positive `amount` |
| `increase_savings` | positive `amount` |
| `extra_debt_payment` | `loan_id` or `account_id`, positive `amount`, optional `date` |
| `delay_purchase` | positive `amount`, `new_date`, optional `original_date` |
| `modify_recurring` | `recurring_id`, and either `cancel: true` or positive `new_amount` |
| `change_income` | exactly one of `amount` or `percent`, optional `effective_date` |

The response contains full `baseline` and `proposed` balance series, comparable summaries,
`delta`, confidence, and a deterministic trade-off note.

## Affordability

```json
POST /affordability/check
{"amount": "30000.00", "target_date": "2026-10-03"}
```

The verdict is `affordable`, `caution`, or `not_affordable`, based on the simulated
minimum cash balance and the user's preferred buffer.
