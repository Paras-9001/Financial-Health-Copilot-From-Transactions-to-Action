import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Account,
    CashFlowForecast,
    Category,
    IncomeSource,
    RecurringTransaction,
    Transaction,
)
from app.forecast.service import (
    add_calendar_months,
    classify_forecast_confidence,
    generate_forecast,
)
from app.recurring.service import detect_recurring_patterns

PERSONA_FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "phase3_personas.json").read_text(encoding="utf-8")
)


def transaction(
    *,
    txn_date: date,
    amount: str,
    category: Category,
    merchant_id=None,
    direction: str = "debit",
) -> Transaction:
    return Transaction(
        id=uuid4(),
        account_id=uuid4(),
        txn_date=txn_date,
        amount=Decimal(amount),
        direction=direction,
        raw_description="fixture",
        category_id=category.id,
        merchant_id=merchant_id,
        dedup_hash=str(uuid4()),
    )


def auth(client, email: str):
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "correct horse battery", "name": "Forecast User"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_calendar_months_do_not_drift():
    assert add_calendar_months(date(2026, 1, 31)) == date(2026, 2, 28)
    assert add_calendar_months(date(2024, 1, 31)) == date(2024, 2, 29)
    assert add_calendar_months(date(2026, 11, 30), 3) == date(2027, 2, 28)


def test_confidence_degrades_with_history_volatility_and_coverage():
    assert classify_forecast_confidence(90, Decimal("0.10"), Decimal("85")) == "high"
    assert classify_forecast_confidence(45, Decimal("0.10"), Decimal("75")) == "medium"
    assert classify_forecast_confidence(29, Decimal("0.10"), Decimal("90")) == "low"
    assert classify_forecast_confidence(90, Decimal("0.36"), Decimal("90")) == "low"
    assert classify_forecast_confidence(90, Decimal("0.10"), Decimal("49")) == "low"


def test_scheduled_flows_and_daily_spending_are_both_applied():
    category = Category(id=uuid4(), name="Groceries", type="variable")
    as_of = date(2026, 9, 30)
    transactions = [
        transaction(
            txn_date=as_of - timedelta(days=offset),
            amount="10.00",
            category=category,
        )
        for offset in range(30)
    ]
    recurring = RecurringTransaction(
        id=uuid4(),
        user_id=uuid4(),
        expected_amount=Decimal("100.00"),
        frequency="monthly",
        next_expected_date=as_of + timedelta(days=1),
        confirmed_cycles=3,
        status="confirmed",
    )
    income = IncomeSource(
        id=uuid4(),
        user_id=uuid4(),
        name="Biweekly income",
        amount=Decimal("200.00"),
        frequency="biweekly",
        last_received_date=as_of - timedelta(days=13),
    )
    result = generate_forecast(
        accounts=[Account(id=uuid4(), user_id=uuid4(), type="checking", name="Cash", balance=1000)],
        transactions=transactions,
        recurring=[recurring],
        income_sources=[income],
        category_map={category.id: category},
        loans=[],
        horizon_days=1,
    )
    point = result.daily_projection[0]
    assert point.scheduled_inflow == Decimal("200.00")
    assert point.scheduled_outflow == Decimal("100.00")
    assert point.unscheduled_spend == Decimal("10.00")
    assert point.projected_balance == Decimal("1090.00")


def test_detected_recurring_spend_is_not_counted_again_as_unscheduled():
    category = Category(id=uuid4(), name="Groceries", type="variable")
    recurring_id = uuid4()
    transactions = [
        transaction(
            txn_date=date(2026, month, 15),
            amount="100.00",
            category=category,
        )
        for month in (7, 8, 9)
    ]
    for item in transactions:
        item.recurring_id = recurring_id
    result = generate_forecast(
        accounts=[Account(id=uuid4(), user_id=uuid4(), type="checking", name="Cash", balance=1000)],
        transactions=transactions,
        recurring=[],
        income_sources=[],
        category_map={category.id: category},
        loans=[],
        horizon_days=1,
    )
    assert result.daily_projection[0].unscheduled_spend == Decimal("0.00")


def test_recurring_detection_uses_amount_and_interval_tolerances():
    category = Category(id=uuid4(), name="Subscriptions", type="fixed")
    merchant_id = uuid4()
    transactions = [
        transaction(
            txn_date=txn_date,
            amount=amount,
            category=category,
            merchant_id=merchant_id,
        )
        for txn_date, amount in (
            (date(2026, 7, 19), "649.00"),
            (date(2026, 8, 19), "655.00"),
            (date(2026, 9, 19), "645.00"),
        )
    ]
    patterns = detect_recurring_patterns(transactions, {category.id: category})
    assert len(patterns) == 1
    assert patterns[0].status == "confirmed"
    assert patterns[0].frequency == "monthly"
    assert patterns[0].confirmed_cycles == 3
    assert patterns[0].expected_amount == Decimal("649.67")
    assert patterns[0].next_expected_date == date(2026, 10, 19)


def test_recurring_detection_ignores_structured_debt_payments():
    category = Category(id=uuid4(), name="Debt Payment", type="fixed")
    merchant_id = uuid4()
    transactions = [
        transaction(
            txn_date=date(2026, month, 5),
            amount="8000.00",
            category=category,
            merchant_id=merchant_id,
        )
        for month in (7, 8, 9)
    ]
    assert detect_recurring_patterns(transactions, {category.id: category}) == []


def test_forecast_requires_transactions_and_valid_horizon():
    with pytest.raises(ValueError):
        generate_forecast([], [], [], [], {}, [], 30)
    category = Category(id=uuid4(), name="Dining", type="discretionary")
    transactions = [transaction(txn_date=date(2026, 9, 1), amount="10", category=category)]
    with pytest.raises(ValueError):
        generate_forecast([], transactions, [], [], {category.id: category}, [], 0)


@pytest.mark.parametrize("persona", ["ananya", "rohit", "meera"])
def test_forecast_endpoint_returns_chart_data_for_every_persona(client, persona):
    headers = auth(client, f"{persona}.forecast@example.com")
    assert (
        client.post("/api/v1/onboarding/demo", json={"persona": persona}, headers=headers).status_code == 201
    )
    response = client.get("/api/v1/cash-flow/forecast?horizon_days=30", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "rolling_average_v1"
    assert data["horizon_days"] == 30
    assert len(data["daily_projection"]) == 30
    assert data["daily_projection"][0]["date"] > data["as_of_date"]
    assert data["daily_projection"][-1]["date"] > data["daily_projection"][0]["date"]
    assert data["confidence"] in ("low", "medium", "high")
    assert len(data["assumptions"]) == 3
    expected = PERSONA_FIXTURES[persona]
    for field in (
        "as_of_date",
        "history_days",
        "spending_cv",
        "recurring_coverage_pct",
        "confidence",
    ):
        assert data[field] == expected[field]
    for index, point in expected["sample_points"].items():
        assert data["daily_projection"][int(index)] == point


def test_forecast_endpoint_validates_and_handles_no_data(client):
    headers = auth(client, "forecast-errors@example.com")
    assert client.get("/api/v1/cash-flow/forecast", headers=headers).status_code == 404
    assert client.get("/api/v1/cash-flow/forecast?horizon_days=0", headers=headers).status_code == 422
    assert client.get("/api/v1/cash-flow/forecast?horizon_days=91", headers=headers).status_code == 422


def test_forecast_and_recurring_results_are_persisted(client, db_engine):
    headers = auth(client, "forecast-persistence@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    assert client.get("/api/v1/cash-flow/forecast", headers=headers).status_code == 200
    with Session(db_engine) as db:
        assert db.scalar(select(func.count()).select_from(CashFlowForecast)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(RecurringTransaction)
                .where(RecurringTransaction.status == "confirmed")
            )
            >= 4
        )


def test_recurring_expenses_endpoint(client):
    headers = auth(client, "recurring-api@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    response = client.get("/api/v1/recurring-expenses", headers=headers)
    assert response.status_code == 200
    items = response.json()["recurring"]
    assert any(item["merchant"] == "Netflix" and item["status"] == "confirmed" for item in items)
