"""Requires TEST_DATABASE_URL pointing to a dedicated, migrated PostgreSQL test DB."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="No dedicated PostgreSQL TEST_DATABASE_URL configured")
EXPECTED = {
    "users",
    "accounts",
    "categories",
    "merchants",
    "transactions",
    "recurring_transactions",
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
}


def test_migrated_schema_and_money_precision():
    engine = create_engine(URL)
    try:
        tables = set(inspect(engine).get_table_names())
        assert tables == EXPECTED | {"alembic_version"}
        amount = next(c for c in inspect(engine).get_columns("transactions") if c["name"] == "amount")
        assert (amount["type"].precision, amount["type"].scale) == (14, 2)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0002_chat_schema"
    finally:
        engine.dispose()


def test_owner_safe_loan_link_and_cascade():
    engine = create_engine(URL)
    try:
        with engine.connect() as c:
            tx = c.begin()
            try:
                a, b, account = str(uuid4()), str(uuid4()), str(uuid4())
                for uid in [a, b]:
                    c.execute(
                        text("INSERT INTO users(id,email,password_hash) VALUES (:id,:email,'test-hash')"),
                        {"id": uid, "email": uid + "@example.com"},
                    )
                c.execute(
                    text("INSERT INTO accounts(id,user_id,type,name) VALUES (:id,:uid,'checking','Test')"),
                    {"id": account, "uid": a},
                )
                with pytest.raises(IntegrityError), c.begin_nested():
                    c.execute(
                        text(
                            "INSERT INTO loans(user_id,account_id,principal,interest_rate,term_months,start_date,monthly_installment,outstanding_balance) VALUES (:uid,:account,100,1,12,'2026-09-27',10,100)"
                        ),
                        {"uid": b, "account": account},
                    )
                c.execute(text("DELETE FROM users WHERE id=:id"), {"id": a})
                assert c.scalar(text("SELECT count(*) FROM accounts WHERE id=:id"), {"id": account}) == 0
            finally:
                tx.rollback()
    finally:
        engine.dispose()
