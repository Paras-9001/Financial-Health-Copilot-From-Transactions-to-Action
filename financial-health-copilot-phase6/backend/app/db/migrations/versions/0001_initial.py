"""Initial schema from supplied DATABASE_SCHEMA.md; frozen Phase 0 DDL.

Domain ORM models/repositories and data seeding are Phase 1 work.
Additional checks and owner-safe loan/risk links are documented in PHASE_0_DECISIONS.md.
"""

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

UPGRADE_SQL = [
    "CREATE TABLE users (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    email TEXT NOT NULL UNIQUE CHECK (email = lower(email)),\n    password_hash TEXT NOT NULL, name TEXT,\n    preferred_buffer_days INT NOT NULL DEFAULT 7 CONSTRAINT ck_users_buffer CHECK (preferred_buffer_days >= 0),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE accounts (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, type TEXT NOT NULL CHECK (type IN ('checking','savings','credit_card','loan','investment')),\n    name TEXT NOT NULL, balance NUMERIC(14,2) NOT NULL DEFAULT 0, currency TEXT NOT NULL DEFAULT 'INR', UNIQUE(user_id, id),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE categories (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    name TEXT NOT NULL UNIQUE, type TEXT NOT NULL CHECK (type IN ('fixed','variable','discretionary','income','transfer')),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE merchants (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    raw_pattern TEXT NOT NULL, normalized_name TEXT NOT NULL, default_category_id UUID REFERENCES categories(id),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE recurring_transactions (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, merchant_id UUID REFERENCES merchants(id), expected_amount NUMERIC(14,2) NOT NULL CHECK (expected_amount > 0),\n    amount_variance_pct NUMERIC(5,2), frequency TEXT NOT NULL CHECK (frequency IN ('weekly','monthly','yearly')),\n    next_expected_date DATE, confirmed_cycles INT NOT NULL DEFAULT 0 CHECK (confirmed_cycles >= 0),\n    status TEXT NOT NULL CHECK (status IN ('confirmed','candidate')),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE transactions (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE, txn_date DATE NOT NULL,\n    amount NUMERIC(14,2) NOT NULL CHECK (amount <> 0), direction TEXT NOT NULL CHECK (direction IN ('debit','credit')),\n    raw_description TEXT NOT NULL, merchant_id UUID REFERENCES merchants(id), category_id UUID REFERENCES categories(id),\n    recurring_id UUID REFERENCES recurring_transactions(id) ON DELETE SET NULL,\n    is_manual_override BOOLEAN NOT NULL DEFAULT false, dedup_hash TEXT NOT NULL, UNIQUE(account_id, dedup_hash),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE loans (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, account_id UUID,\n    principal NUMERIC(14,2) NOT NULL CHECK (principal > 0), interest_rate NUMERIC(5,2) NOT NULL CHECK (interest_rate >= 0),\n    term_months INT NOT NULL CHECK (term_months > 0), start_date DATE NOT NULL,\n    monthly_installment NUMERIC(14,2) NOT NULL CHECK (monthly_installment > 0), outstanding_balance NUMERIC(14,2) NOT NULL CHECK (outstanding_balance >= 0),\n    FOREIGN KEY (user_id, account_id) REFERENCES accounts(user_id, id),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE loan_payments (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    loan_id UUID NOT NULL REFERENCES loans(id) ON DELETE CASCADE, payment_date DATE NOT NULL,\n    amount NUMERIC(14,2) NOT NULL CHECK (amount > 0), principal_component NUMERIC(14,2) NOT NULL CHECK (principal_component >= 0),\n    interest_component NUMERIC(14,2) NOT NULL CHECK (interest_component >= 0), is_extra_payment BOOLEAN NOT NULL DEFAULT false,\n    CHECK (amount = principal_component + interest_component),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE credit_cards (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    account_id UUID NOT NULL UNIQUE REFERENCES accounts(id) ON DELETE CASCADE,\n    credit_limit NUMERIC(14,2) NOT NULL CHECK (credit_limit > 0), current_balance NUMERIC(14,2) NOT NULL,\n    statement_date INT NOT NULL CHECK (statement_date BETWEEN 1 AND 31),\n    minimum_due NUMERIC(14,2) NOT NULL CHECK (minimum_due >= 0), apr NUMERIC(5,2) CHECK (apr >= 0),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE investments (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    account_id UUID NOT NULL UNIQUE REFERENCES accounts(id) ON DELETE CASCADE,\n    holding_type TEXT NOT NULL CHECK (holding_type IN ('mutual_fund','stocks','fd','other')),\n    current_value NUMERIC(14,2) NOT NULL CHECK (current_value >= 0), as_of_date DATE NOT NULL,\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE income_sources (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, name TEXT NOT NULL, amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),\n    frequency TEXT NOT NULL CHECK (frequency IN ('monthly','biweekly','irregular')), is_variable BOOLEAN NOT NULL DEFAULT false, last_received_date DATE,\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE budgets (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, category_id UUID NOT NULL REFERENCES categories(id), period TEXT NOT NULL DEFAULT 'monthly' CHECK (period = 'monthly'), target_amount NUMERIC(14,2) NOT NULL CHECK (target_amount >= 0),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE financial_snapshots (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, snapshot_time TIMESTAMPTZ NOT NULL DEFAULT now(),\n    total_income NUMERIC(14,2), total_expenses NUMERIC(14,2), fixed_expenses NUMERIC(14,2), variable_expenses NUMERIC(14,2), discretionary_expenses NUMERIC(14,2), savings NUMERIC(14,2),\n    savings_rate NUMERIC(5,2), debt_to_income NUMERIC(5,2), debt_service_ratio NUMERIC(5,2),\n    cash_buffer_days NUMERIC(6,1), health_score NUMERIC(5,1), metric_period_start DATE, metric_period_end DATE,\n    CHECK (metric_period_end >= metric_period_start),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE cash_flow_forecasts (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, generated_at TIMESTAMPTZ NOT NULL DEFAULT now(), horizon_days INT NOT NULL CHECK (horizon_days > 0),\n    daily_projection JSONB NOT NULL CHECK (jsonb_typeof(daily_projection) = 'array'), method TEXT NOT NULL,\n    confidence TEXT NOT NULL CHECK (confidence IN ('low','medium','high')),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE risk_events (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, risk_type TEXT NOT NULL, severity TEXT NOT NULL CHECK (severity IN ('low','medium','high')),\n    evidence JSONB NOT NULL, confidence NUMERIC(4,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),\n    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(), resolved_at TIMESTAMPTZ,\n    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','resolved')), UNIQUE(user_id, id),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE recommendations (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, risk_event_id UUID, title TEXT NOT NULL, reason TEXT NOT NULL, evidence JSONB NOT NULL,\n    action JSONB NOT NULL, confidence NUMERIC(4,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),\n    priority TEXT NOT NULL CHECK (priority IN ('P0','P1','P2')), assumptions JSONB, generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),\n    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','resolved','superseded')),\n    FOREIGN KEY (user_id, risk_event_id) REFERENCES risk_events(user_id, id),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE recommendation_impacts (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    recommendation_id UUID NOT NULL UNIQUE REFERENCES recommendations(id) ON DELETE CASCADE,\n    baseline JSONB NOT NULL, proposed JSONB NOT NULL, delta_summary JSONB NOT NULL,\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE chat_sessions (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, started_at TIMESTAMPTZ NOT NULL DEFAULT now(),\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE TABLE chat_messages (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,\n    role TEXT NOT NULL CHECK (role IN ('user','assistant','tool')), content TEXT NOT NULL, tool_calls JSONB,\n    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n)",
    "CREATE INDEX idx_accounts_user ON accounts(user_id)",
    "CREATE INDEX idx_txn_account_date ON transactions(account_id, txn_date)",
    "CREATE INDEX idx_txn_category ON transactions(category_id)",
    "CREATE INDEX idx_snapshot_user_time ON financial_snapshots(user_id, snapshot_time DESC)",
    "CREATE INDEX idx_risk_user_status ON risk_events(user_id, status)",
    "CREATE INDEX idx_reco_user_status ON recommendations(user_id, status)",
    "CREATE INDEX idx_chat_msg_session ON chat_messages(session_id, created_at)",
    "CREATE INDEX idx_loans_user ON loans(user_id)",
    "CREATE INDEX idx_recurring_user ON recurring_transactions(user_id)",
    "CREATE INDEX idx_income_user ON income_sources(user_id)",
    "CREATE INDEX idx_forecast_user ON cash_flow_forecasts(user_id, generated_at DESC)",
]
TABLES = [
    "users",
    "accounts",
    "categories",
    "merchants",
    "recurring_transactions",
    "transactions",
    "loans",
    "loan_payments",
    "credit_cards",
    "investments",
    "income_sources",
    "budgets",
    "financial_snapshots",
    "cash_flow_forecasts",
    "risk_events",
    "recommendations",
    "recommendation_impacts",
    "chat_sessions",
    "chat_messages",
]


def upgrade():
    for statement in UPGRADE_SQL:
        op.execute(statement)


def downgrade():
    for name in reversed(TABLES):
        op.execute(f'DROP TABLE "{name}"')
