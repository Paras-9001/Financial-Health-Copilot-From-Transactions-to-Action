# Phase 2 Financial Analytics API Reference

Base URL: `/api/v1`. All endpoints require `Authorization: Bearer <JWT>`.

---

## 1. `GET /financial-summary`

- **Purpose:** Return the core financial health summary, facts, ratios, and composite health score.
- **Query Parameters:**
  - `start_date` (optional, `YYYY-MM-DD`): start of analysis period.
  - `end_date` (optional, `YYYY-MM-DD`): end of analysis period (defaults to trailing 30 days).
- **Response 200:**
```json
{
  "period": {
    "start": "2026-08-27",
    "end": "2026-09-26"
  },
  "facts": {
    "total_income": "60000.00",
    "total_expenses": "48000.00",
    "savings": "12000.00",
    "savings_rate": "20.00",
    "fixed_expenses": "27000.00",
    "variable_expenses": "10010.00",
    "discretionary_expenses": "10990.00",
    "monthly_burn": "48000.00",
    "cash_buffer_days": "5.6",
    "emergency_fund_months": "5.6"
  },
  "ratios": {
    "debt_to_income": "15.80",
    "recurring_burden_pct": "46.70",
    "credit_utilization": "22.00",
    "debt_service_ratio": "15.80",
    "expense_to_income": "80.00"
  },
  "health_score": {
    "value": 71,
    "confidence": "high"
  }
}
```
- **Errors:**
  - `404 no_data`: returned when user has zero transactions.
  - `422 validation_error`: returned if `end_date < start_date`.

---

## 2. `GET /spending/by-category`

- **Purpose:** Spending breakdown by category for the period.
- **Query Parameters:** `start_date?`, `end_date?`
- **Response 200:**
```json
{
  "categories": [
    {
      "name": "Rent",
      "amount": "15000.00",
      "pct_of_total": "31.25",
      "type": "fixed"
    },
    {
      "name": "Debt Payment",
      "amount": "8000.00",
      "pct_of_total": "16.67",
      "type": "fixed"
    },
    {
      "name": "Dining",
      "amount": "7110.00",
      "pct_of_total": "14.81",
      "type": "discretionary"
    },
    {
      "name": "Shopping",
      "amount": "7280.00",
      "pct_of_total": "15.17",
      "type": "discretionary"
    },
    {
      "name": "Groceries",
      "amount": "6000.00",
      "pct_of_total": "12.50",
      "type": "variable"
    }
  ]
}
```

---

## 3. `GET /debt/summary`

- **Purpose:** Aggregate view of user's debts, credit cards, DTI, and credit utilization.
- **Response 200:**
```json
{
  "total_debt": "110000.00",
  "dti": "15.80",
  "debt_service_ratio": "15.80",
  "credit_utilization": "22.00",
  "loans": [
    {
      "id": "c1387d89-9a2e-4bdf-8772-c518df4f54ab",
      "principal": "160000.00",
      "interest_rate": "12.00",
      "term_months": 24,
      "monthly_installment": "8000.00",
      "outstanding_balance": "88000.00"
    }
  ],
  "credit_cards": [
    {
      "id": "e987c2b1-6a1f-4efc-8b22-83b3f2df7901",
      "credit_limit": "100000.00",
      "current_balance": "22000.00",
      "statement_date": 18,
      "minimum_due": "1500.00",
      "apr": "36.00"
    }
  ]
}
```
- **Errors:**
  - `404 no_debt_data`: returned when user has zero loans and zero credit cards.

---

## 4. `GET /debt/loans/{id}/amortization`

- **Purpose:** Full month-by-month loan repayment and interest amortization schedule.
- **Response 200:**
```json
{
  "schedule": [
    {
      "date": "2025-12-05",
      "principal_component": "6400.00",
      "interest_component": "1600.00",
      "remaining_balance": "153600.00"
    },
    ...
    {
      "date": "2027-10-05",
      "principal_component": "7920.79",
      "interest_component": "79.21",
      "remaining_balance": "0.00"
    }
  ]
}
```
- **Errors:**
  - `404 loan_not_found`: returned if loan ID does not exist or belongs to another user.
