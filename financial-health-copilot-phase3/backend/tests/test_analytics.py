import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.service import (
    calculate_cash_buffer_days,
    calculate_coefficient_of_variation,
    calculate_confidence,
    calculate_confidence_score,
    calculate_credit_utilization,
    calculate_debt_service_ratio,
    calculate_debt_to_income,
    calculate_discretionary_expenses,
    calculate_emergency_fund_months,
    calculate_expense_to_income,
    calculate_fixed_expenses,
    calculate_health_score,
    calculate_income_volatility,
    calculate_loan_amortization,
    calculate_monthly_burn,
    calculate_monthly_history,
    calculate_monthly_recurring_obligations,
    calculate_recurring_burden_pct,
    calculate_savings,
    calculate_savings_rate,
    calculate_spending_by_category,
    calculate_spending_volatility,
    calculate_total_expenses,
    calculate_total_income,
    calculate_variable_expenses,
)
from app.db.models import (
    Category,
    CreditCard,
    FinancialSnapshot,
    IncomeSource,
    RecurringTransaction,
    Transaction,
)

PERSONA_FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "phase2_personas.json").read_text(encoding="utf-8")
)

# =============================================================================
# Unit Tests for Pure Financial Analytics Functions
# =============================================================================


def test_pure_income_and_expense_calculations():
    cat_inc = Category(id=uuid4(), name="Income", type="income")
    cat_rent = Category(id=uuid4(), name="Rent", type="fixed")
    cat_groc = Category(id=uuid4(), name="Groceries", type="variable")
    cat_dine = Category(id=uuid4(), name="Dining", type="discretionary")
    cat_trans = Category(id=uuid4(), name="Transfer", type="transfer")
    cat_map = {c.id: c for c in [cat_inc, cat_rent, cat_groc, cat_dine, cat_trans]}

    account_id = uuid4()
    txns = [
        Transaction(
            account_id=account_id,
            txn_date=date(2026, 9, 1),
            amount=Decimal("60000.00"),
            direction="credit",
            category_id=cat_inc.id,
            raw_description="Salary",
            dedup_hash="h1",
        ),
        Transaction(
            account_id=account_id,
            txn_date=date(2026, 9, 1),
            amount=Decimal("15000.00"),
            direction="debit",
            category_id=cat_rent.id,
            raw_description="Rent",
            dedup_hash="h2",
        ),
        Transaction(
            account_id=account_id,
            txn_date=date(2026, 9, 10),
            amount=Decimal("6000.00"),
            direction="debit",
            category_id=cat_groc.id,
            raw_description="BigBasket",
            dedup_hash="h3",
        ),
        Transaction(
            account_id=account_id,
            txn_date=date(2026, 9, 15),
            amount=Decimal("7200.00"),
            direction="debit",
            category_id=cat_dine.id,
            raw_description="Swiggy",
            dedup_hash="h4",
        ),
        Transaction(
            account_id=account_id,
            txn_date=date(2026, 9, 20),
            amount=Decimal("5000.00"),
            direction="debit",
            category_id=cat_trans.id,
            raw_description="Transfer",
            dedup_hash="h5",
        ),
    ]

    income = calculate_total_income(txns, cat_map)
    assert income == Decimal("60000.00")

    # Transfer of 5000 is excluded from total expenses
    expenses = calculate_total_expenses(txns, cat_map)
    assert expenses == Decimal("28200.00")  # 15000 + 6000 + 7200

    fixed = calculate_fixed_expenses(txns, cat_map)
    assert fixed == Decimal("15000.00")

    variable = calculate_variable_expenses(txns, cat_map)
    assert variable == Decimal("6000.00")

    discretionary = calculate_discretionary_expenses(txns, cat_map)
    assert discretionary == Decimal("7200.00")

    savings = calculate_savings(income, expenses)
    assert savings == Decimal("31800.00")

    savings_rate = calculate_savings_rate(income, expenses)
    assert savings_rate == Decimal("53.00")

    exp_to_inc = calculate_expense_to_income(expenses, income)
    assert exp_to_inc == Decimal("47.00")


def test_fallback_income_sources():
    cat_map = {}
    sources = [
        IncomeSource(
            id=uuid4(), user_id=uuid4(), name="Job", amount=Decimal("50000.00"), frequency="monthly"
        ),
        IncomeSource(
            id=uuid4(), user_id=uuid4(), name="Side", amount=Decimal("10000.00"), frequency="monthly"
        ),
    ]
    # No transactions, fallback to declared income sources
    income = calculate_total_income([], cat_map, sources)
    assert income == Decimal("60000.00")


def test_savings_rate_zero_or_negative_income():
    assert calculate_savings_rate(Decimal("0.00"), Decimal("5000.00")) == Decimal("0.00")
    assert calculate_expense_to_income(Decimal("5000.00"), Decimal("0.00")) == Decimal("0.00")
    assert calculate_savings(Decimal("1000.00"), Decimal("2500.00")) == Decimal("-1500.00")


def test_debt_ratios():
    # Example from FINANCIAL_ANALYTICS.md: EMI ₹8,000 + Card min-due ₹1,500 on income ₹60,000 → DTI = 15.8%
    dti = calculate_debt_to_income(Decimal("9500.00"), Decimal("60000.00"))
    assert dti == Decimal("15.83")  # quantizes to 15.83

    dsr = calculate_debt_service_ratio(Decimal("9500.00"), Decimal("60000.00"))
    assert dsr == Decimal("15.83")

    assert calculate_debt_to_income(Decimal("9500.00"), Decimal("0.00")) == Decimal("0.00")


def test_monthly_burn_and_cash_buffer():
    # 30-day period with 48000 expenses
    burn = calculate_monthly_burn(Decimal("48000.00"), 30)
    assert burn == Decimal("48000.00")

    # Example from FINANCIAL_ANALYTICS.md: Balance ₹9,000, avg daily expense ₹1,600 → buffer ≈ 5.6 days
    buffer_days = calculate_cash_buffer_days(Decimal("9000.00"), Decimal("1600.00"))
    assert buffer_days == Decimal("5.6")

    # Zero expense edge case
    assert calculate_cash_buffer_days(Decimal("9000.00"), Decimal("0.00")) is None


def test_emergency_fund_months():
    # Liquid savings 60,000, avg monthly expense 30,000 -> 2.0 months
    ef = calculate_emergency_fund_months(Decimal("60000.00"), Decimal("30000.00"))
    assert ef == Decimal("2.0")

    assert calculate_emergency_fund_months(Decimal("60000.00"), Decimal("0.00")) is None


def test_recurring_burden_pct():
    # Example from FINANCIAL_ANALYTICS.md: Recurring obligations ₹28,000 on income ₹60,000 → 46.7%
    burden = calculate_recurring_burden_pct(Decimal("28000.00"), Decimal("60000.00"))
    assert burden == Decimal("46.67")


def test_credit_utilization():
    card1 = CreditCard(
        id=uuid4(),
        account_id=uuid4(),
        credit_limit=Decimal("60000.00"),
        current_balance=Decimal("12000.00"),
        statement_date=1,
        minimum_due=Decimal("1200.00"),
    )
    card2 = CreditCard(
        id=uuid4(),
        account_id=uuid4(),
        credit_limit=Decimal("40000.00"),
        current_balance=Decimal("10000.00"),
        statement_date=1,
        minimum_due=Decimal("1000.00"),
    )
    # Total limit 100,000, balance 22,000 -> 22.00%
    util = calculate_credit_utilization([card1, card2])
    assert util == Decimal("22.00")

    assert calculate_credit_utilization([]) == Decimal("0.00")


def test_volatility_coefficient_of_variation():
    # Stable series: CV should be very low
    stable_incomes = [Decimal("60000"), Decimal("60000"), Decimal("60500"), Decimal("59500")]
    cv_stable = calculate_income_volatility(stable_incomes)
    assert cv_stable < Decimal("0.05")

    # Variable series: Rohit (35k to 95k) -> CV around 0.38
    variable_incomes = [
        Decimal("35000"),
        Decimal("95000"),
        Decimal("42000"),
        Decimal("88000"),
        Decimal("47000"),
    ]
    cv_var = calculate_income_volatility(variable_incomes)
    assert cv_var >= Decimal("0.30")  # crosses HIGH threshold

    # Single or empty value
    assert calculate_coefficient_of_variation([Decimal("50000")]) == Decimal("0.00")
    assert calculate_spending_volatility([]) == Decimal("0.00")


def test_monthly_history_keeps_zero_months():
    income = Category(id=uuid4(), name="Income", type="income")
    dining = Category(id=uuid4(), name="Dining", type="discretionary")
    account_id = uuid4()
    txns = [
        Transaction(
            account_id=account_id,
            txn_date=date(2026, 1, 5),
            amount=Decimal("100.00"),
            direction="credit",
            category_id=income.id,
            raw_description="Income",
            dedup_hash="jan-income",
        ),
        Transaction(
            account_id=account_id,
            txn_date=date(2026, 3, 5),
            amount=Decimal("30.00"),
            direction="debit",
            category_id=dining.id,
            raw_description="Dining",
            dedup_hash="mar-dining",
        ),
    ]
    incomes, spending = calculate_monthly_history(
        txns, {income.id: income, dining.id: dining}, date(2026, 3, 31)
    )
    assert incomes == [Decimal("100.00"), Decimal("0.00"), Decimal("0.00")]
    assert spending == [Decimal("0.00"), Decimal("0.00"), Decimal("30.00")]


def test_recurring_obligations_are_monthly_normalized():
    user_id = uuid4()
    recurring = [
        RecurringTransaction(
            user_id=user_id,
            expected_amount=Decimal("1200.00"),
            frequency="yearly",
            status="confirmed",
        ),
        RecurringTransaction(
            user_id=user_id,
            expected_amount=Decimal("100.00"),
            frequency="weekly",
            status="confirmed",
        ),
        RecurringTransaction(
            user_id=user_id,
            expected_amount=Decimal("999.00"),
            frequency="monthly",
            status="candidate",
        ),
    ]
    assert calculate_monthly_recurring_obligations(recurring) == Decimal("533.33")


def test_health_score_ananya():
    # Ananya's exact parameters:
    # savings_rate = 20.00%
    # dti = 15.80%
    # credit_util = 22.00%
    # buffer_days = 5.6
    # recurring_burden = 46.70%
    score = calculate_health_score(
        savings_rate=Decimal("20.00"),
        debt_to_income=Decimal("15.80"),
        credit_utilization=Decimal("22.00"),
        cash_buffer_days=Decimal("5.6"),
        preferred_buffer_days=7,
        recurring_burden_pct=Decimal("46.70"),
    )
    assert score == 71


def test_confidence_calculation():
    # Complete, fresh data with low volatility
    conf = calculate_confidence(
        data_completeness=Decimal("1.0"),
        data_freshness=Decimal("1.0"),
        historical_consistency=Decimal("0.98"),
        forecast_uncertainty=Decimal("0.8"),
        observation_count_periods=3,
    )
    assert conf == "high"

    # Degraded data completeness and stale freshness
    conf_degraded = calculate_confidence(
        data_completeness=Decimal("0.3"),
        data_freshness=Decimal("0.2"),
        historical_consistency=Decimal("0.4"),
        forecast_uncertainty=Decimal("0.4"),
        observation_count_periods=1,
    )
    assert conf_degraded == "low"

    score = calculate_confidence_score(observation_count_periods=6)
    assert score == Decimal("0.96")
    with pytest.raises(ValueError):
        calculate_confidence_score(data_completeness=Decimal("1.01"))


def test_loan_amortization():
    schedule = calculate_loan_amortization(
        principal=Decimal("10000.00"),
        interest_rate=Decimal("12.00"),
        term_months=3,
        monthly_installment=Decimal("3400.00"),
        start_date=date(2026, 1, 1),
    )
    assert len(schedule) == 3
    assert schedule[0]["date"] == "2026-02-01"
    # Check that final balance is 0.00
    assert schedule[-1]["remaining_balance"] == "0.00"
    for item in schedule:
        assert Decimal(item["principal_component"]) > 0
        assert Decimal(item["interest_component"]) >= 0

    with pytest.raises(ValueError):
        calculate_loan_amortization(
            principal=Decimal("0"),
            interest_rate=Decimal("12"),
            term_months=3,
            monthly_installment=Decimal("100"),
            start_date=date(2026, 1, 1),
        )


def test_spending_by_category():
    cat_rent = Category(id=uuid4(), name="Rent", type="fixed")
    cat_dine = Category(id=uuid4(), name="Dining", type="discretionary")
    cat_trans = Category(id=uuid4(), name="Transfer", type="transfer")
    cat_map = {c.id: c for c in [cat_rent, cat_dine, cat_trans]}

    account_id = uuid4()
    txns = [
        Transaction(
            account_id=account_id,
            txn_date=date(2026, 9, 1),
            amount=Decimal("15000.00"),
            direction="debit",
            category_id=cat_rent.id,
            raw_description="Rent",
            dedup_hash="h1",
        ),
        Transaction(
            account_id=account_id,
            txn_date=date(2026, 9, 2),
            amount=Decimal("5000.00"),
            direction="debit",
            category_id=cat_dine.id,
            raw_description="Swiggy",
            dedup_hash="h2",
        ),
        Transaction(
            account_id=account_id,
            txn_date=date(2026, 9, 3),
            amount=Decimal("2000.00"),
            direction="debit",
            category_id=cat_trans.id,
            raw_description="Transfer",
            dedup_hash="h3",
        ),
    ]

    items = calculate_spending_by_category(txns, cat_map)
    # Transfer is excluded, total expense is 20000
    assert len(items) == 2
    assert items[0]["name"] == "Rent"
    assert items[0]["amount"] == "15000.00"
    assert items[0]["pct_of_total"] == "75.00"

    assert items[1]["name"] == "Dining"
    assert items[1]["amount"] == "5000.00"
    assert items[1]["pct_of_total"] == "25.00"


# =============================================================================
# API Integration Tests for Financial Analytics Endpoints
# =============================================================================


def auth(client, email="analytics@example.com"):
    payload = {"email": email, "password": "correct horse battery", "name": "Analytics User"}
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_financial_summary_no_data(client):
    # Fresh user with 0 transactions
    headers = auth(client, "nodata@example.com")
    response = client.get("/api/v1/financial-summary", headers=headers)
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "no_data"


@pytest.mark.parametrize("persona", ["ananya", "rohit", "meera"])
def test_persona_financial_summary_matches_hand_computed_fixture(client, persona):
    headers = auth(client, f"{persona}.fixture@example.com")
    seed_res = client.post("/api/v1/onboarding/demo", json={"persona": persona}, headers=headers)
    assert seed_res.status_code == 201

    res = client.get("/api/v1/financial-summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    expected = PERSONA_FIXTURES[persona]

    assert data["period"] == expected["period"]
    assert data["facts"] == expected["facts"]
    assert data["ratios"] == expected["ratios"]
    assert data["health_score"] == expected["health_score"]
    assert data["data_quality"] == {
        "observation_periods": expected["observation_periods"],
        "insufficient_history": False,
        "uncategorized_transactions": 0,
    }


def test_financial_summary_persists_snapshot(client, db_engine):
    headers = auth(client, "snapshot.test@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    assert client.get("/api/v1/financial-summary", headers=headers).status_code == 200
    with Session(db_engine) as db:
        assert db.scalar(select(func.count()).select_from(FinancialSnapshot)) == 1


def test_financial_summary_marks_short_history_as_low_confidence(client):
    headers = auth(client, "short-history.test@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    response = client.get(
        "/api/v1/financial-summary?start_date=2026-07-01&end_date=2026-07-31",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data_quality"]["observation_periods"] == 1
    assert data["data_quality"]["insufficient_history"] is True
    assert data["health_score"]["confidence"] == "low"
    assert Decimal(data["health_score"]["confidence_score"]) < Decimal("0.40")


def test_spending_by_category_api(client):
    headers = auth(client, "category.test@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    res = client.get("/api/v1/spending/by-category", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "categories" in data
    assert len(data["categories"]) > 0
    # Rent should be largest expense
    assert data["categories"][0]["name"] == "Rent"
    assert data["categories"][0]["amount"] == "15000.00"


def test_debt_summary_api(client):
    headers = auth(client, "debt.test@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    res = client.get("/api/v1/debt/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["loans"]) == 1
    assert len(data["credit_cards"]) == 1
    assert data["credit_utilization"] == "22.00"
    assert data["loans"][0]["monthly_installment"] == "8000.00"
    assert data["credit_cards"][0]["current_balance"] == "22000.00"


def test_debt_summary_no_debt(client):
    headers = auth(client, "nodebt.test@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "meera"}, headers=headers)
    res = client.get("/api/v1/debt/summary", headers=headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "no_debt_data"


def test_loan_amortization_api(client):
    headers = auth(client, "amort.test@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    debt_res = client.get("/api/v1/debt/summary", headers=headers)
    loan_id = debt_res.json()["loans"][0]["id"]

    res = client.get(f"/api/v1/debt/loans/{loan_id}/amortization", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "schedule" in data
    assert len(data["schedule"]) in (23, 24)
    assert data["schedule"][-1]["remaining_balance"] == "0.00"


def test_loan_amortization_not_found(client):
    headers = auth(client, "loan404.test@example.com")
    random_id = str(uuid4())
    res = client.get(f"/api/v1/debt/loans/{random_id}/amortization", headers=headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "loan_not_found"


def test_date_validation_error(client):
    headers = auth(client, "dateval.test@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    res = client.get(
        "/api/v1/financial-summary?start_date=2026-09-20&end_date=2026-09-10",
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"
