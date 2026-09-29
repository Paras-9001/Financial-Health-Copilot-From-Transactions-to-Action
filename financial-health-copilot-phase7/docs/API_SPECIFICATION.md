# API Specification

Base URL: `/api/v1`. All endpoints except `/auth/*` require `Authorization: Bearer <JWT>`. All monetary values are decimal strings in INR unless noted. All errors follow:
```json
{ "error": { "code": "string", "message": "string", "details": {} } }
```

## Public vs. Internal

All endpoints below are **public** (called by the frontend). There are no internal-only endpoints in the MVP — the modular monolith means analytics/forecast/risk/recommendation modules are called in-process by the API layer, not exposed as separate services.

---

## Authentication

### `POST /auth/signup`
- **Purpose:** Create a user account.
- **Request:** `{ "email": "a@b.com", "password": "string", "name": "string" }`
- **Response 201:** `{ "user_id": "uuid", "token": "jwt" }`
- **Errors:** `409 email_exists`, `422 validation_error` (weak password, invalid email)

### `POST /auth/login`
- **Request:** `{ "email": "...", "password": "..." }`
- **Response 200:** `{ "token": "jwt", "user": { "id", "email", "name" } }`
- **Errors:** `401 invalid_credentials`

---

## Users

### `GET /users/me`
- **Response 200:** `{ "id", "email", "name", "preferred_buffer_days" }`

### `PATCH /users/me`
- **Request:** `{ "preferred_buffer_days"?: int, "name"?: string }`
- **Response 200:** updated user object

---

## Accounts

### `GET /accounts`
- **Response 200:** `{ "accounts": [ { "id", "type", "name", "balance", "currency" } ] }`

### `POST /accounts`
- **Request:** `{ "type", "name", "balance", "currency"? }`
- **Response 201:** created account
- **Errors:** `422 invalid_type`

---

## Transactions

### `GET /transactions`
- **Query params:** `category_id?, merchant?, start_date?, end_date?, min_amount?, max_amount?, page?, page_size?`
- **Response 200:** `{ "transactions": [...], "total_count", "page" }`

### `POST /transactions`
- **Purpose:** Ingest one or more transactions (bulk-friendly for demo seeding and "new transaction arrives" demo trigger).
- **Request:** `{ "transactions": [ { "account_id", "txn_date", "amount", "direction", "raw_description" } ] }`
- **Response 201:** `{ "ingested": int, "duplicates_skipped": int, "recalculation_triggered": true }`
- **Errors:** `422 validation_error` (bad date/amount), each rejected row reported individually in `details`.

### `PATCH /transactions/{id}`
- **Purpose:** Manual category correction.
- **Request:** `{ "category_id": "uuid" }`
- **Response 200:** updated transaction; triggers recalculation.

---

## Categories

### `GET /categories`
- **Response 200:** `{ "categories": [ { "id", "name", "type" } ] }`

---

## Financial Summary

### `GET /financial-summary`
- **Query params:** `start_date?, end_date?` (default trailing 30 days)
- **Response 200:**
```json
{
  "period": { "start": "2026-08-27", "end": "2026-09-26" },
  "facts": { "total_income": "60000.00", "total_expenses": "48000.00", "savings": "12000.00", "savings_rate": "20.00" },
  "ratios": { "debt_to_income": "15.80", "recurring_burden_pct": "46.70", "credit_utilization": "22.00" },
  "health_score": { "value": 71, "confidence": "high" }
}
```
- **Errors:** `404 no_data` if user has zero transactions.

---

## Spending Analytics

### `GET /spending/by-category`
- **Query params:** `start_date?, end_date?`
- **Response 200:** `{ "categories": [ { "name", "amount", "pct_of_total", "type" } ] }`

---

## Recurring Expenses

### `GET /recurring-expenses`
- **Response 200:** `{ "recurring": [ { "id", "merchant", "amount", "frequency", "next_expected_date", "status" } ] }`

---

## Debt

### `GET /debt/summary`
- **Response 200:** `{ "total_debt": "...", "dti": "...", "debt_service_ratio": "...", "credit_utilization": "...", "loans": [...], "credit_cards": [...] }`
- **Errors:** `404 no_debt_data`

### `GET /debt/loans/{id}/amortization`
- **Response 200:** `{ "schedule": [ { "date", "principal_component", "interest_component", "remaining_balance" } ] }`

---

## Cash-Flow Forecast

### `GET /cash-flow/forecast`
- **Query params:** `horizon_days?` (default 30, max 90)
- **Response 200:** `{ "as_of_date", "horizon_days", "daily_projection": [ { "date", "projected_balance", "lower_bound", "upper_bound", "scheduled_inflow", "scheduled_outflow", "unscheduled_spend" } ], "confidence", "method": "rolling_average_v1", "history_days", "spending_cv", "recurring_coverage_pct", "assumptions": [...] }`
- **Errors:** `404 no_data`, `422 validation_error` for a horizon outside 1–90 days.

---

## Risk Events

### `GET /risks`
- **Query params:** `status?` (default `active`)
- **Response 200:** `{ "risks": [ { "id", "risk_type", "severity", "evidence", "confidence", "detected_at" } ] }`

---

## Recommendations

### `GET /recommendations`
- **Query params:** `status?` (default `active`)
- **Response 200:** `{ "recommendations": [ { ...see RECOMMENDATION_ENGINE.md schema... } ] }`

### `GET /recommendations/{id}/history`
- **Purpose:** Show how this recommendation (or the risk behind it) has changed over time.
- **Response 200:** `{ "timeline": [ { "timestamp", "status", "expected_impact" } ] }`

---

## Affordability

### `POST /affordability/check`
- **Request:** `{ "amount": "30000.00", "target_date": "2026-10-03" }`
- **Response 200:** `{ "verdict": "caution", "resulting_buffer_days": 2, "confidence": "medium", "reasoning_basis": [...] }`
- **Errors:** `422 invalid_amount`

---

## What-If Simulation

### `POST /simulate`
- **Request:**
```json
{ "action_type": "extra_debt_payment", "params": { "loan_id": "uuid", "amount": "10000.00", "date": "2026-10-05" }, "horizon_days": 90 }
```
- **Response 200:** `{ ...see IMPACT_SIMULATION.md output structure... }`
- **Notes:** `horizon_days` is optional (default `90`, range `1–180`).
- **Errors:** `422 invalid_action` (e.g., amount exceeds outstanding balance), `404 loan_not_found`

---

## Chat

### `POST /chat/sessions`
- **Response 201:** `{ "session_id": "uuid" }`

### `POST /chat/sessions/{id}/messages`
- **Request:** `{ "message": "Can I afford a ₹30,000 laptop next week?" }`
- **Response 200:**
```json
{
  "answer_text": "...",
  "facts": [...],
  "predictions": [...],
  "recommendations": [...],
  "tool_calls": [ { "tool": "calculate_affordability", "args": {...} } ]
}
```
- **Errors:** `503 llm_unavailable` (deterministic fallback message returned instead of a hard failure), `422 empty_message`

### `GET /chat/sessions/{id}/messages`
- **Response 200:** `{ "messages": [ { "role", "content", "created_at" } ] }`
