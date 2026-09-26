# Data Architecture

## Conceptual Entities

- **User** — the account holder.
- **Account** — a checking/savings/credit-card/loan/investment account owned by a user.
- **Transaction** — a single debit/credit event on an account.
- **Merchant** — normalized counterparty of a transaction, used for categorization and recurring detection.
- **Category** — the fixed taxonomy a transaction is classified into.
- **RecurringPayment** — a detected or declared repeating obligation (subscription, rent, EMI).
- **IncomeSource** — a declared or detected source of recurring income.
- **Loan** — a debt obligation with principal/rate/term/schedule.
- **LoanPayment** — an individual payment event against a loan.
- **CreditCard** — a credit account with limit/balance/statement cycle.
- **Investment** — a holding snapshot (balance only in MVP).
- **Budget** — an optional user-declared spending target per category/period (P1).
- **FinancialSnapshot** — a persisted, timestamped set of computed metrics for a user (for history/diffing).
- **CashFlowForecast** — a persisted forecast run, with projected values and confidence.
- **RiskEvent** — a detected risk/opportunity, with evidence and severity.
- **Recommendation** — a generated action, with expected impact and confidence.
- **RecommendationImpact** — the quantified before/after comparison tied to a recommendation.
- **ChatSession / ChatMessage** — conversational history for the AI copilot.

## Relationships

- A **User** has many **Accounts**, **IncomeSources**, **Loans**, **Budgets**, **ChatSessions**.
- An **Account** has many **Transactions**.
- A **Transaction** belongs to one **Merchant** (nullable if unrecognized) and one **Category**.
- A **Transaction** may belong to a **RecurringPayment** (nullable).
- A **Loan** has many **LoanPayments**.
- A **User** has many **FinancialSnapshots**, **CashFlowForecasts**, **RiskEvents**, **Recommendations** over time (append-only, timestamped).
- A **Recommendation** has one **RecommendationImpact** (the quantified expected-impact payload) and references the **RiskEvent**(s) that generated it as evidence.
- A **ChatSession** has many **ChatMessages**; a **ChatMessage** may reference the tool calls/results that grounded it.

## Why Append-Only History Matters

The product requires demonstrating that recommendations change as new data arrives (FR-H1–H4). `FinancialSnapshot`, `CashFlowForecast`, `RiskEvent`, and `Recommendation` are therefore never overwritten in place — each recalculation inserts a new timestamped row referencing the same `user_id`, so the system (and the demo) can show a before/after diff.

## Entity-Relationship Diagram

```mermaid
erDiagram
    USER ||--o{ ACCOUNT : owns
    USER ||--o{ INCOME_SOURCE : declares
    USER ||--o{ LOAN : has
    USER ||--o{ BUDGET : sets
    USER ||--o{ FINANCIAL_SNAPSHOT : has
    USER ||--o{ CASH_FLOW_FORECAST : has
    USER ||--o{ RISK_EVENT : has
    USER ||--o{ RECOMMENDATION : receives
    USER ||--o{ CHAT_SESSION : starts

    ACCOUNT ||--o{ TRANSACTION : records
    ACCOUNT ||--o| CREDIT_CARD : "is a"
    ACCOUNT ||--o| INVESTMENT : "is a"

    MERCHANT ||--o{ TRANSACTION : "counterparty of"
    CATEGORY ||--o{ TRANSACTION : classifies

    RECURRING_PAYMENT ||--o{ TRANSACTION : groups

    LOAN ||--o{ LOAN_PAYMENT : has

    RISK_EVENT ||--o{ RECOMMENDATION : generates
    RECOMMENDATION ||--|| RECOMMENDATION_IMPACT : quantifies

    CHAT_SESSION ||--o{ CHAT_MESSAGE : contains

    USER {
        uuid id
        string email
        string name
    }
    ACCOUNT {
        uuid id
        uuid user_id
        string type
        numeric balance
    }
    TRANSACTION {
        uuid id
        uuid account_id
        date txn_date
        numeric amount
        string direction
        uuid merchant_id
        uuid category_id
        uuid recurring_id
    }
    LOAN {
        uuid id
        uuid user_id
        numeric principal
        numeric interest_rate
        int term_months
    }
    RISK_EVENT {
        uuid id
        uuid user_id
        string risk_type
        string severity
        float confidence
    }
    RECOMMENDATION {
        uuid id
        uuid user_id
        uuid risk_event_id
        string title
        string priority
        float confidence
    }
