"""Phase 7 integration acceptance tests."""


def _auth(client, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "phase-seven-passphrase", "name": "Phase Seven"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_scenario_7_live_contract_updates_balance_and_financial_state(client):
    headers = _auth(client, "phase7-scenario@example.com")
    seeded = client.post(
        "/api/v1/onboarding/demo",
        json={"persona": "ananya"},
        headers=headers,
    )
    assert seeded.status_code == 201

    before_summary = client.get("/api/v1/financial-summary", headers=headers).json()
    before_risks = client.get("/api/v1/risks", headers=headers).json()["risks"]
    before_recommendations = client.get(
        "/api/v1/recommendations", headers=headers
    ).json()["recommendations"]
    accounts = client.get("/api/v1/accounts", headers=headers).json()["accounts"]
    checking = next(account for account in accounts if account["type"] == "checking")
    assert checking["balance"] == "9000.00"

    added = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "transactions": [
                {
                    "account_id": checking["id"],
                    "txn_date": "2026-09-28",
                    "amount": "12000.00",
                    "direction": "debit",
                    "raw_description": "UNPLANNED MEDICAL EXPENSE",
                }
            ]
        },
    )
    assert added.status_code == 201
    assert added.json()["recalculation_triggered"] is True

    after_accounts = client.get("/api/v1/accounts", headers=headers).json()["accounts"]
    after_checking = next(account for account in after_accounts if account["id"] == checking["id"])
    assert after_checking["balance"] == "-3000.00"

    transactions = client.get(
        "/api/v1/transactions?merchant=Medical", headers=headers
    ).json()["transactions"]
    assert len(transactions) == 1
    categories = client.get("/api/v1/categories", headers=headers).json()["categories"]
    healthcare = next(category for category in categories if category["name"] == "Healthcare")
    assert transactions[0]["category_id"] == healthcare["id"]

    after_summary = client.get("/api/v1/financial-summary", headers=headers).json()
    after_risks = client.get("/api/v1/risks", headers=headers).json()["risks"]
    after_recommendations = client.get(
        "/api/v1/recommendations", headers=headers
    ).json()["recommendations"]

    assert after_summary["facts"]["total_expenses"] != before_summary["facts"]["total_expenses"]
    assert after_summary["facts"]["cash_buffer_days"] != before_summary["facts"]["cash_buffer_days"]
    assert {
        (risk["risk_type"], str(risk["evidence"])) for risk in after_risks
    } != {(risk["risk_type"], str(risk["evidence"])) for risk in before_risks}
    assert after_recommendations
    assert [item["title"] for item in after_recommendations] != [
        item["title"] for item in before_recommendations
    ]
