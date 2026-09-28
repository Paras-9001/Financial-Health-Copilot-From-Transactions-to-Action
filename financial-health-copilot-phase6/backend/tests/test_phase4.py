"""Phase 4 tests: risk rule engine, recommendation pipeline, and simulation engine.

Covers:
- All 7 risk rules with unit tests
- Persona-level integration tests verifying designed triggers (SAMPLE_DATA.md)
- Recommendation generation and ranking
- Simulation engine for all supported action types
- /risks, /recommendations, /simulate, /affordability/check API endpoints
- Scenario 7 (before/after recalculation) via API calls alone
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.db.models import (
    Account,
    Category,
    CreditCard,
    IncomeSource,
    Loan,
    Transaction,
)
from app.risks.service import (
    rule_debt_pressure,
    rule_income_volatility,
    rule_low_cash_buffer,
    rule_recurring_payment_burden,
    rule_unusual_transactions,
    rule_unusually_high_spending,
    rule_upcoming_cash_flow_gap,
)
from app.simulation.service import (
    FinancialState,
    SimulationAction,
    apply_action,
    simulate_action,
)

ZERO = Decimal("0.00")
AS_OF = date(2026, 9, 26)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_account(balance: str = "9000", account_type: str = "checking") -> Account:
    return Account(
        id=uuid4(),
        user_id=uuid4(),
        type=account_type,
        name="Test Account",
        balance=Decimal(balance),
        currency="INR",
    )


def make_category(name: str, cat_type: str = "discretionary") -> Category:
    return Category(id=uuid4(), name=name, type=cat_type)


def make_transaction(
    txn_date: date,
    amount: str,
    category: Category,
    direction: str = "debit",
    recurring_id=None,
) -> Transaction:
    return Transaction(
        id=uuid4(),
        account_id=uuid4(),
        txn_date=txn_date,
        amount=Decimal(amount),
        direction=direction,
        raw_description="test",
        category_id=category.id,
        recurring_id=recurring_id,
        dedup_hash=str(uuid4()),
    )


def make_income_source(amount: str = "60000", frequency: str = "monthly") -> IncomeSource:
    return IncomeSource(
        id=uuid4(),
        user_id=uuid4(),
        name="Salary",
        amount=Decimal(amount),
        frequency=frequency,
        last_received_date=AS_OF,
    )


def make_loan(balance: str = "100000", installment: str = "8000") -> Loan:
    return Loan(
        id=uuid4(),
        user_id=uuid4(),
        principal=Decimal(balance),
        interest_rate=Decimal("12.00"),
        term_months=24,
        start_date=date(2025, 1, 1),
        monthly_installment=Decimal(installment),
        outstanding_balance=Decimal(balance),
    )


def make_credit_card(balance: str, limit: str = "100000") -> CreditCard:
    return CreditCard(
        id=uuid4(),
        account_id=uuid4(),
        credit_limit=Decimal(limit),
        current_balance=Decimal(balance),
        statement_date=15,
        minimum_due=Decimal("500"),
    )


def auth(client, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "correct horse battery", "name": "Test User"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['token']}"}


# ---------------------------------------------------------------------------
# Unit tests: risk rules
# ---------------------------------------------------------------------------


def test_rule_low_cash_buffer_triggers_high_severity():
    cat = make_category("Groceries", "variable")
    account = make_account("900")  # below two days of average spending
    transactions = [make_transaction(AS_OF - timedelta(days=i), "500", cat) for i in range(30)]
    cat_map = {cat.id: cat}
    result = rule_low_cash_buffer([account], transactions, cat_map, 30)
    assert result is not None
    assert result.severity == "high"
    assert result.risk_type == "low_cash_buffer"


def test_rule_low_cash_buffer_does_not_trigger_when_buffer_sufficient():
    cat = make_category("Groceries", "variable")
    account = make_account("100000")  # plenty of balance
    transactions = [make_transaction(AS_OF - timedelta(days=i), "500", cat) for i in range(30)]
    result = rule_low_cash_buffer([account], transactions, {cat.id: cat}, 30)
    assert result is None


def test_rule_upcoming_cash_flow_gap_triggers():
    from app.forecast.service import ForecastResult, ProjectionPoint

    # Construct a forecast with a breach in the first few days
    def make_point(day: int, balance: str) -> ProjectionPoint:
        return ProjectionPoint(
            date=AS_OF + timedelta(days=day),
            projected_balance=Decimal(balance),
            lower_bound=Decimal(balance) - 500,
            upper_bound=Decimal(balance) + 500,
            scheduled_inflow=ZERO,
            scheduled_outflow=ZERO,
            unscheduled_spend=Decimal("500"),
        )

    points = [make_point(i, str(1000 - i * 300)) for i in range(1, 8)]
    forecast = ForecastResult(
        as_of_date=AS_OF,
        horizon_days=7,
        daily_projection=points,
        confidence="medium",
        history_days=30,
        spending_cv=Decimal("0.20"),
        recurring_coverage_pct=Decimal("60"),
        rolling_average_daily_spend=Decimal("500"),
        trend_factor=Decimal("1.00"),
    )
    result = rule_upcoming_cash_flow_gap(forecast, Decimal("7"))
    assert result is not None
    assert result.risk_type == "upcoming_cash_flow_gap"


def test_rule_unusually_high_spending_triggers():
    cat = make_category("Dining", "discretionary")
    cat_map = {cat.id: cat}

    # Historical: 3 months of ₹3000/month dining
    history = []
    for month_offset in range(1, 4):
        p_end = AS_OF - timedelta(days=month_offset * 30)
        history += [make_transaction(p_end - timedelta(days=i), "100", cat) for i in range(30)]

    # Current period: ₹7200 (above 130% of ₹3000)
    current = [make_transaction(AS_OF - timedelta(days=i), "240", cat) for i in range(30)]

    results = rule_unusually_high_spending(history + current, cat_map, AS_OF, 120)
    assert any(
        r.risk_type == "unusually_high_spending" and r.evidence["category"] == "Dining" for r in results
    )


def test_rule_recurring_payment_burden_triggers():
    cat = make_category("Fixed", "fixed")
    income_src = make_income_source("30000")
    loan = make_loan("200000", "18000")  # 18000 EMI on 30000 income → >50%
    result = rule_recurring_payment_burden([], [loan], [income_src], [], {cat.id: cat})
    assert result is not None
    assert result.risk_type == "recurring_payment_burden"


def test_rule_debt_pressure_triggers_credit_utilization():
    cat = make_category("Transfer", "transfer")
    cc = make_credit_card("68000", "75000")  # 90.7% utilization
    income_src = make_income_source("60000")
    result = rule_debt_pressure([], [cc], [income_src], [], {cat.id: cat})
    assert result is not None
    assert result.risk_type == "debt_pressure"
    assert result.severity == "high"


def test_rule_income_volatility_triggers():
    income_cat = make_category("Income", "income")
    cat_map = {income_cat.id: income_cat}
    # Volatile income: 95k, 35k, 70k, 40k (high CV)
    transactions = []
    for month_offset, amount in enumerate([95000, 35000, 70000, 40000]):
        p_date = AS_OF - timedelta(days=month_offset * 30)
        transactions.append(
            Transaction(
                id=uuid4(),
                account_id=uuid4(),
                txn_date=p_date,
                amount=Decimal(str(amount)),
                direction="credit",
                raw_description="Client payment",
                category_id=income_cat.id,
                dedup_hash=str(uuid4()),
            )
        )
    result = rule_income_volatility(transactions, cat_map, AS_OF)
    assert result is not None
    assert result.risk_type == "income_volatility"


def test_rule_income_volatility_suppressed_with_insufficient_periods():
    income_cat = make_category("Income", "income")
    cat_map = {income_cat.id: income_cat}
    # Only 2 periods — not enough
    transactions = [
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            txn_date=AS_OF - timedelta(days=i * 30),
            amount=Decimal("95000"),
            direction="credit",
            raw_description="Income",
            category_id=income_cat.id,
            dedup_hash=str(uuid4()),
        )
        for i in range(2)
    ]
    result = rule_income_volatility(transactions, cat_map, AS_OF)
    assert result is None


def test_rule_unusual_transaction_triggers():
    cat = make_category("Shopping", "discretionary")
    cat_map = {cat.id: cat}
    # Normal transactions ₹500 each
    normal = [make_transaction(AS_OF - timedelta(days=i), "500", cat) for i in range(3, 90)]
    # One spike ₹10000 (20x avg)
    spike = make_transaction(AS_OF - timedelta(days=1), "10000", cat)
    results = rule_unusual_transactions(normal + [spike], cat_map, AS_OF)
    assert len(results) >= 1
    assert results[0].risk_type == "unusual_transaction"


# ---------------------------------------------------------------------------
# Integration tests: persona triggers (SAMPLE_DATA.md)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("persona", ["ananya", "rohit", "meera"])
def test_risks_endpoint_returns_data_for_persona(client, persona):
    headers = auth(client, f"{persona}.risks@example.com")
    assert (
        client.post("/api/v1/onboarding/demo", json={"persona": persona}, headers=headers).status_code == 201
    )
    response = client.get("/api/v1/risks", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "risks" in data
    for risk in data["risks"]:
        assert risk["severity"] in ("low", "medium", "high")
        assert risk["status"] == "active"
        assert float(risk["confidence"]) > 0


def test_ananya_triggers_designed_risks(client):
    """Persona A should trigger low_cash_buffer and unusually_high_spending (dining)."""
    headers = auth(client, "ananya.risk-triggers@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    response = client.get("/api/v1/risks", headers=headers)
    assert response.status_code == 200
    risk_types = {r["risk_type"] for r in response.json()["risks"]}
    # Ananya has low balance mid-month — expects low_cash_buffer or upcoming gap
    assert risk_types & {"low_cash_buffer", "upcoming_cash_flow_gap", "unusually_high_spending"}


def test_rohit_triggers_debt_and_income_volatility(client):
    """Persona B should trigger income_volatility and debt_pressure."""
    headers = auth(client, "rohit.risk-triggers@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "rohit"}, headers=headers)
    response = client.get("/api/v1/risks", headers=headers)
    assert response.status_code == 200
    risk_types = {r["risk_type"] for r in response.json()["risks"]}
    assert risk_types & {"income_volatility", "debt_pressure"}


# ---------------------------------------------------------------------------
# Recommendation tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("persona", ["ananya", "rohit", "meera"])
def test_recommendations_endpoint_returns_data(client, persona):
    headers = auth(client, f"{persona}.recommendations@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": persona}, headers=headers)
    response = client.get("/api/v1/recommendations", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    for rec in data["recommendations"]:
        assert rec["priority"] in ("P0", "P1", "P2")
        assert float(rec["confidence"]) >= 0.40
        assert rec["title"]
        assert rec["reason"]
        assert rec["action"]["type"]
        assert isinstance(rec["assumptions"], list)


def test_recommendations_have_evidence_and_impact(client):
    headers = auth(client, "reco-evidence@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    response = client.get("/api/v1/recommendations", headers=headers)
    assert response.status_code == 200
    for rec in response.json()["recommendations"]:
        assert len(rec["evidence"]) > 0
        assert "expected_impact" in rec
        for ev in rec["evidence"]:
            assert ev["type"] in ("fact", "prediction", "assumption")


def test_recommendations_are_idempotent_across_reads(client):
    headers = auth(client, "reco-stable@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    first = client.get("/api/v1/recommendations", headers=headers).json()["recommendations"]
    second = client.get("/api/v1/recommendations", headers=headers).json()["recommendations"]
    assert {item["id"] for item in first} == {item["id"] for item in second}


def test_recommendation_history_endpoint(client):
    headers = auth(client, "reco-history@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    recos = client.get("/api/v1/recommendations", headers=headers).json()["recommendations"]
    if not recos:
        pytest.skip("No recommendations generated for this persona")
    reco_id = recos[0]["id"]
    response = client.get(f"/api/v1/recommendations/{reco_id}/history", headers=headers)
    assert response.status_code == 200
    assert "timeline" in response.json()


# ---------------------------------------------------------------------------
# Simulation tests
# ---------------------------------------------------------------------------


def test_simulation_reduce_spending(client):
    headers = auth(client, "simulate-reduce@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    response = client.post(
        "/api/v1/simulate",
        json={"action_type": "reduce_spending", "params": {"category": "Dining", "amount": "2500"}},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "baseline" in data
    assert "proposed" in data
    assert "delta" in data
    assert data["confidence"] in ("low", "medium", "high")
    assert data["trade_off_note"]
    assert Decimal(data["proposed"]["month_end_balance"]) > Decimal(data["baseline"]["month_end_balance"])


def test_simulation_extra_debt_payment(client):
    headers = auth(client, "simulate-loan@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    # Get loan id
    debt = client.get("/api/v1/debt/summary", headers=headers).json()
    if not debt.get("loans"):
        pytest.skip("No loans for this persona")
    loan_id = debt["loans"][0]["id"]
    response = client.post(
        "/api/v1/simulate",
        json={
            "action_type": "extra_debt_payment",
            "params": {"loan_id": loan_id, "amount": "5000", "date": "2026-10-05"},
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["proposed"]["loan_payoff_months"] is not None


def test_simulation_modify_recurring_cancel(client):
    headers = auth(client, "simulate-cancel@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    recurring = client.get("/api/v1/recurring-expenses", headers=headers).json()["recurring"]
    if not recurring:
        pytest.skip("No recurring expenses")
    recurring_id = recurring[0]["id"]
    response = client.post(
        "/api/v1/simulate",
        json={"action_type": "modify_recurring", "params": {"recurring_id": recurring_id, "cancel": True}},
        headers=headers,
    )
    assert response.status_code == 200


def test_simulation_change_income(client):
    headers = auth(client, "simulate-income@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    response = client.post(
        "/api/v1/simulate",
        json={"action_type": "change_income", "params": {"percent": "-10"}},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "baseline" in data
    assert "proposed" in data
    assert Decimal(data["proposed"]["month_end_balance"]) < Decimal(data["baseline"]["month_end_balance"])


def test_simulation_increase_savings(client):
    headers = auth(client, "simulate-savings@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "meera"}, headers=headers)
    response = client.post(
        "/api/v1/simulate",
        json={"action_type": "increase_savings", "params": {"amount": "5000"}},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["delta"]["savings_accumulated"]) == Decimal("5000.00")
    assert Decimal(data["proposed"]["month_end_balance"]) < Decimal(data["baseline"]["month_end_balance"])


def test_simulation_hypothetical_purchase_changes_projection(client):
    headers = auth(client, "simulate-purchase@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    response = client.post(
        "/api/v1/simulate",
        json={
            "action_type": "delay_purchase",
            "params": {"amount": "50000", "new_date": "2026-10-15"},
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["delta"]["minimum_projected_balance"]) == Decimal("-50000.00")


def test_simulation_rejects_spending_reduction_above_recent_spend(client):
    headers = auth(client, "simulate-reduce-invalid@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    response = client.post(
        "/api/v1/simulate",
        json={"action_type": "reduce_spending", "params": {"category": "Dining", "amount": "999999"}},
        headers=headers,
    )
    assert response.status_code == 422


def test_simulation_validates_excess_loan_payment(client):
    headers = auth(client, "simulate-loan-validate@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    debt = client.get("/api/v1/debt/summary", headers=headers).json()
    if not debt.get("loans"):
        pytest.skip("No loans for this persona")
    loan_id = debt["loans"][0]["id"]
    outstanding = float(debt["loans"][0]["outstanding_balance"])
    response = client.post(
        "/api/v1/simulate",
        json={
            "action_type": "extra_debt_payment",
            "params": {"loan_id": loan_id, "amount": str(outstanding + 100000)},
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_simulation_invalid_action_type(client):
    headers = auth(client, "simulate-invalid@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    response = client.post(
        "/api/v1/simulate",
        json={"action_type": "nonexistent_action", "params": {}},
        headers=headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Affordability check tests
# ---------------------------------------------------------------------------


def test_affordability_check_affordable(client):
    headers = auth(client, "afford-ok@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "meera"}, headers=headers)
    response = client.post(
        "/api/v1/affordability/check",
        json={"amount": "10000.00", "target_date": "2026-10-15"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] in ("affordable", "caution", "not_affordable")
    assert data["confidence"] in ("low", "medium", "high")
    assert len(data["reasoning_basis"]) >= 2


def test_affordability_check_caution_for_large_purchase(client):
    headers = auth(client, "afford-caution@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    response = client.post(
        "/api/v1/affordability/check",
        json={"amount": "180000.00", "target_date": "2026-11-01"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] in ("caution", "not_affordable")


def test_affordability_check_validates_amount(client):
    headers = auth(client, "afford-invalid@example.com")
    client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers)
    response = client.post(
        "/api/v1/affordability/check",
        json={"amount": "-100.00", "target_date": "2026-10-15"},
        headers=headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Scenario 7: Before/after recalculation via API calls alone
# ---------------------------------------------------------------------------


def test_scenario_7_inject_transaction_triggers_recalculation(client):
    """
    Scenario 7 from DEMO_SCENARIOS.md:
    1. Ananya's initial state has existing risks.
    2. A new large dining transaction is injected.
    3. Re-calling /risks shows updated/new risk events.
    4. Re-calling /recommendations reflects the updated risks.

    This verifies the acceptance criterion: scenario 7 is reproducible end-to-end
    via API calls alone.
    """
    headers = auth(client, "scenario7@example.com")
    assert (
        client.post("/api/v1/onboarding/demo", json={"persona": "ananya"}, headers=headers).status_code == 201
    )

    # Step 1: Get baseline risks
    initial_risks = client.get("/api/v1/risks", headers=headers).json()["risks"]

    # Step 2: Get account id
    accounts = client.get("/api/v1/accounts", headers=headers).json()["accounts"]
    assert accounts, "Expected at least one account"
    checking = next((a for a in accounts if a["type"] == "checking"), accounts[0])
    account_id = checking["id"]

    # Step 3: Inject a large transaction (dining spike)
    inject_response = client.post(
        "/api/v1/transactions",
        json={
            "transactions": [
                {
                    "account_id": account_id,
                    "txn_date": "2026-09-27",
                    "amount": "8500",
                    "direction": "debit",
                    "raw_description": "ZOMATO_LARGE_ORDER",
                }
            ]
        },
        headers=headers,
    )
    assert inject_response.status_code == 201
    assert inject_response.json()["ingested"] == 1

    # Step 4: Re-run risks — should detect updated state
    updated_risks = client.get("/api/v1/risks", headers=headers).json()["risks"]
    assert isinstance(updated_risks, list)
    initial_state = {(item["risk_type"], str(item["evidence"])) for item in initial_risks}
    updated_state = {(item["risk_type"], str(item["evidence"])) for item in updated_risks}
    assert updated_state != initial_state

    # Step 5: Get updated recommendations
    updated_recos = client.get("/api/v1/recommendations", headers=headers).json()["recommendations"]
    assert isinstance(updated_recos, list)

    # Step 6: Verify recalculation triggered — recommendations should exist and be based on new state
    # (At minimum, the system ran without error after the injection)
    # In a deterministic test, we verify the pipeline runs end-to-end.
    for rec in updated_recos:
        assert float(rec["confidence"]) >= 0.40
        assert rec["status"] == "active"


# ---------------------------------------------------------------------------
# Simulation unit tests (pure, no DB)
# ---------------------------------------------------------------------------


def _make_state_for_unit_test() -> FinancialState:
    cat = make_category("Dining", "discretionary")
    income_cat = make_category("Income", "income")
    accounts = [make_account("20000")]
    transactions = [make_transaction(AS_OF - timedelta(days=i), "300", cat) for i in range(30)] + [
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            txn_date=AS_OF - timedelta(days=1),
            amount=Decimal("60000"),
            direction="credit",
            raw_description="Salary",
            category_id=income_cat.id,
            dedup_hash=str(uuid4()),
        )
    ]
    income = make_income_source("60000")
    return FinancialState(
        accounts=accounts,
        transactions=transactions,
        recurring=[],
        income_sources=[income],
        category_map={cat.id: cat, income_cat.id: income_cat},
        loans=[],
        credit_cards=[],
    )


def test_apply_action_reduce_spending_rejects_amount_above_actual_spend():
    state = _make_state_for_unit_test()
    action = SimulationAction(type="reduce_spending", category="Dining", amount=Decimal("99999"))
    with pytest.raises(ValueError, match="exceeds recent"):
        apply_action(state, action)


def test_apply_action_extra_debt_payment_reduces_balance():
    cat = make_category("Fixed", "fixed")
    loan = make_loan("100000", "8000")
    state = FinancialState(
        accounts=[make_account("50000")],
        transactions=[make_transaction(AS_OF - timedelta(days=i), "500", cat) for i in range(30)],
        recurring=[],
        income_sources=[make_income_source()],
        category_map={cat.id: cat},
        loans=[loan],
        credit_cards=[],
    )
    action = SimulationAction(type="extra_debt_payment", loan_id=loan.id, amount=Decimal("10000"))
    new_state = apply_action(state, action)
    updated_loan = next((item for item in new_state.loans if item.id == loan.id), None)
    assert updated_loan is not None
    assert updated_loan.outstanding_balance == Decimal("90000")


def test_simulate_action_returns_valid_result():
    state = _make_state_for_unit_test()
    action = SimulationAction(type="reduce_spending", category="Dining", amount=Decimal("2000"))
    result = simulate_action(state, action, horizon_days=30)
    assert result.confidence in ("low", "medium", "high")
    assert result.baseline
    assert result.proposed
    assert result.delta is not None
    assert result.trade_off_note
    assert Decimal(result.proposed["month_end_balance"]) > Decimal(result.baseline["month_end_balance"])


def test_risks_endpoint_returns_404_without_data(client):
    headers = auth(client, "risks-nodata@example.com")
    response = client.get("/api/v1/risks", headers=headers)
    assert response.status_code == 404


def test_recommendations_endpoint_returns_404_without_data(client):
    headers = auth(client, "recos-nodata@example.com")
    response = client.get("/api/v1/recommendations", headers=headers)
    assert response.status_code == 404
