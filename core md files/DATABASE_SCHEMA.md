# Database Schema

All monetary columns use `NUMERIC(14,2)`. All tables have `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` unless noted, and `created_at TIMESTAMPTZ DEFAULT now()`.

## users

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| email | TEXT | UNIQUE, NOT NULL |
| password_hash | TEXT | NOT NULL |
| name | TEXT | |
| preferred_buffer_days | INT | default 7 — used in affordability/risk logic |
| created_at | TIMESTAMPTZ | |

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    preferred_buffer_days INT NOT NULL DEFAULT 7,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## accounts

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id |
| type | TEXT | CHECK IN ('checking','savings','credit_card','loan','investment') |
| name | TEXT | display name |
| balance | NUMERIC(14,2) | current balance snapshot |
| currency | TEXT | default 'INR' |

```sql
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('checking','savings','credit_card','loan','investment')),
    name TEXT NOT NULL,
    balance NUMERIC(14,2) NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'INR',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_accounts_user ON accounts(user_id);
```

## merchants

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| raw_pattern | TEXT | e.g. 'SWIGGY\*' |
| normalized_name | TEXT | e.g. 'Swiggy' |
| default_category_id | UUID | FK → categories.id, nullable |

## categories

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| name | TEXT | UNIQUE — Groceries, Dining, Transport, Utilities, Rent, Subscriptions, Entertainment, Healthcare, Debt Payment, Income, Transfer, Other |
| type | TEXT | CHECK IN ('fixed','variable','discretionary','income','transfer') |

## transactions

```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    txn_date DATE NOT NULL,
    amount NUMERIC(14,2) NOT NULL CHECK (amount <> 0),
    direction TEXT NOT NULL CHECK (direction IN ('debit','credit')),
    raw_description TEXT NOT NULL,
    merchant_id UUID REFERENCES merchants(id),
    category_id UUID REFERENCES categories(id),
    recurring_id UUID REFERENCES recurring_transactions(id),
    is_manual_override BOOLEAN NOT NULL DEFAULT false,
    dedup_hash TEXT NOT NULL, -- hash(account_id, date, amount, raw_description) for duplicate detection
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (account_id, dedup_hash)
);
CREATE INDEX idx_txn_account_date ON transactions(account_id, txn_date);
CREATE INDEX idx_txn_category ON transactions(category_id);
```

## recurring_transactions

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK |
| merchant_id | UUID | FK |
| expected_amount | NUMERIC(14,2) | midpoint/typical amount |
| amount_variance_pct | NUMERIC(5,2) | e.g. 10.00 |
| frequency | TEXT | 'weekly'/'monthly'/'yearly' |
| next_expected_date | DATE | |
| confirmed_cycles | INT | number of observed occurrences |
| status | TEXT | 'confirmed'/'candidate' |

## loans

```sql
CREATE TABLE loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id),
    principal NUMERIC(14,2) NOT NULL,
    interest_rate NUMERIC(5,2) NOT NULL, -- annual %
    term_months INT NOT NULL,
    start_date DATE NOT NULL,
    monthly_installment NUMERIC(14,2) NOT NULL,
    outstanding_balance NUMERIC(14,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## loan_payments

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| loan_id | UUID | FK → loans.id |
| payment_date | DATE | |
| amount | NUMERIC(14,2) | |
| principal_component | NUMERIC(14,2) | |
| interest_component | NUMERIC(14,2) | |
| is_extra_payment | BOOLEAN | default false |

## credit_cards

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| account_id | UUID | FK → accounts.id, UNIQUE |
| credit_limit | NUMERIC(14,2) | |
| current_balance | NUMERIC(14,2) | |
| statement_date | INT | day of month |
| minimum_due | NUMERIC(14,2) | |
| apr | NUMERIC(5,2) | |

## investments

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| account_id | UUID | FK, UNIQUE |
| holding_type | TEXT | 'mutual_fund'/'stocks'/'fd'/'other' |
| current_value | NUMERIC(14,2) | snapshot only (MVP) |
| as_of_date | DATE | |

## income_sources

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK |
| name | TEXT | e.g. 'Primary Salary' |
| amount | NUMERIC(14,2) | typical amount |
| frequency | TEXT | 'monthly'/'biweekly'/'irregular' |
| is_variable | BOOLEAN | true for freelance/gig income |
| last_received_date | DATE | |

## budgets (P1)

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK |
| category_id | UUID | FK |
| period | TEXT | 'monthly' |
| target_amount | NUMERIC(14,2) | |

## financial_snapshots

```sql
CREATE TABLE financial_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    snapshot_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    total_income NUMERIC(14,2),
    total_expenses NUMERIC(14,2),
    fixed_expenses NUMERIC(14,2),
    variable_expenses NUMERIC(14,2),
    discretionary_expenses NUMERIC(14,2),
    savings NUMERIC(14,2),
    savings_rate NUMERIC(5,2),
    debt_to_income NUMERIC(5,2),
    debt_service_ratio NUMERIC(5,2),
    cash_buffer_days NUMERIC(6,1),
    health_score NUMERIC(5,1),
    metric_period_start DATE,
    metric_period_end DATE
);
CREATE INDEX idx_snapshot_user_time ON financial_snapshots(user_id, snapshot_time DESC);
```

## cash_flow_forecasts

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK |
| generated_at | TIMESTAMPTZ | |
| horizon_days | INT | e.g. 30 |
| daily_projection | JSONB | array of {date, projected_balance, lower_bound, upper_bound} |
| method | TEXT | 'rolling_average_v1' etc. |
| confidence | TEXT | 'low'/'medium'/'high' |

## risk_events

```sql
CREATE TABLE risk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    risk_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('low','medium','high')),
    evidence JSONB NOT NULL,
    confidence NUMERIC(4,2) NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','resolved'))
);
CREATE INDEX idx_risk_user_status ON risk_events(user_id, status);
```

## recommendations

```sql
CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    risk_event_id UUID REFERENCES risk_events(id),
    title TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence JSONB NOT NULL,
    action JSONB NOT NULL,
    confidence NUMERIC(4,2) NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('P0','P1','P2')),
    assumptions JSONB,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','resolved','superseded'))
);
CREATE INDEX idx_reco_user_status ON recommendations(user_id, status);
```

## recommendation_impacts

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| recommendation_id | UUID | FK → recommendations.id, UNIQUE |
| baseline | JSONB | projected values without the action |
| proposed | JSONB | projected values with the action |
| delta_summary | JSONB | key deltas (e.g., buffer_days: +5) |

## chat_sessions / chat_messages

```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user','assistant','tool')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_chat_msg_session ON chat_messages(session_id, created_at);
```
