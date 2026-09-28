from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Transaction
from app.onboarding.service import seed_persona


def auth(client, email="data@example.com"):
    payload = {"email": email, "password": "correct horse battery", "name": "Data User"}
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['token']}"}, response.json()["user_id"]


def create_account(client, headers, name="Daily Checking", account_type="checking"):
    response = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"type": account_type, "name": name, "balance": "10000.00", "currency": "INR"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_transaction_ingestion_partial_validation_and_dedup(client):
    headers, _ = auth(client)
    account = create_account(client, headers)
    valid = {
        "account_id": account["id"],
        "txn_date": "2026-09-17",
        "amount": "620.00",
        "direction": "debit",
        "raw_description": "SWIGGY*ORDER8823",
    }
    response = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={"transactions": [valid, {**valid, "amount": "0"}]},
    )
    assert response.status_code == 201, response.text
    assert response.json()["ingested"] == 1
    assert response.json()["rejected"][0]["row"] == 2

    duplicate = client.post("/api/v1/transactions", headers=headers, json={"transactions": [valid]})
    assert duplicate.status_code == 201
    assert duplicate.json()["ingested"] == 0
    assert duplicate.json()["duplicates_skipped"] == 1

    listed = client.get("/api/v1/transactions", headers=headers).json()
    assert listed["total_count"] == 1
    assert listed["transactions"][0]["amount"] == "620.00"


def test_account_and_transaction_ownership_are_enforced(client):
    first, _ = auth(client, "first@example.com")
    second, _ = auth(client, "second@example.com")
    account = create_account(client, first)
    payload = {
        "account_id": account["id"],
        "txn_date": "2026-09-17",
        "amount": "100",
        "direction": "debit",
        "raw_description": "PRIVATE PURCHASE",
    }
    response = client.post("/api/v1/transactions", headers=second, json={"transactions": [payload]})
    assert response.status_code == 422
    assert response.json()["error"]["details"]["rows"][0]["errors"][0]["field"] == "account_id"
    assert client.get("/api/v1/transactions", headers=second).json()["total_count"] == 0


def test_manual_entry_endpoints(client):
    headers, _ = auth(client)
    loan_account = create_account(client, headers, "Personal Loan", "loan")
    card_account = create_account(client, headers, "Main Card", "credit_card")
    loan = client.post(
        "/api/v1/loans",
        headers=headers,
        json={
            "account_id": loan_account["id"],
            "principal": "120000",
            "interest_rate": "12.5",
            "term_months": 24,
            "start_date": "2026-01-01",
            "monthly_installment": "6000",
            "outstanding_balance": "90000",
        },
    )
    assert loan.status_code == 201, loan.text
    card = client.post(
        "/api/v1/credit-cards",
        headers=headers,
        json={
            "account_id": card_account["id"],
            "credit_limit": "100000",
            "current_balance": "20000",
            "statement_date": 15,
            "minimum_due": "2000",
            "apr": "36",
        },
    )
    assert card.status_code == 201, card.text
    income = client.post(
        "/api/v1/income-sources",
        headers=headers,
        json={
            "name": "Salary",
            "amount": "60000",
            "frequency": "monthly",
            "is_variable": False,
            "last_received_date": "2026-09-01",
        },
    )
    assert income.status_code == 201, income.text
    assert len(client.get("/api/v1/loans", headers=headers).json()["loans"]) == 1
    assert len(client.get("/api/v1/credit-cards", headers=headers).json()["credit_cards"]) == 1
    assert len(client.get("/api/v1/income-sources", headers=headers).json()["income_sources"]) == 1


def test_category_correction_is_remembered_per_user(client):
    headers, _ = auth(client)
    account = create_account(client, headers)
    base = {
        "account_id": account["id"],
        "txn_date": "2026-09-17",
        "amount": "620",
        "direction": "debit",
        "raw_description": "SWIGGY*ORDER8823",
    }
    client.post("/api/v1/transactions", headers=headers, json={"transactions": [base]})
    first = client.get("/api/v1/transactions", headers=headers).json()["transactions"][0]
    categories = client.get("/api/v1/categories", headers=headers).json()["categories"]
    groceries = next(category for category in categories if category["name"] == "Groceries")
    corrected = client.patch(
        f"/api/v1/transactions/{first['id']}",
        headers=headers,
        json={"category_id": groceries["id"]},
    )
    assert corrected.status_code == 200
    second = {**base, "txn_date": "2026-09-18", "raw_description": "SWIGGY*ORDER9999"}
    client.post("/api/v1/transactions", headers=headers, json={"transactions": [second]})
    newest = client.get("/api/v1/transactions", headers=headers).json()["transactions"][0]
    assert newest["category_id"] == groceries["id"]


def test_csv_preview_confirm_partial_rows_and_duplicate_upload(client):
    headers, _ = auth(client)
    csv_content = (
        "date,amount,direction,description,account_name\n"
        "2026-09-20,120.50,debit,UBER TRIP,CSV Checking\n"
        "bad-date,xyz,debit,BROKEN ROW,CSV Checking\n"
        "2026-09-21,60000,credit,SALARY CREDIT,CSV Checking\n"
    )
    preview = client.post(
        "/api/v1/imports/csv/preview",
        headers=headers,
        files={"file": ("transactions.csv", csv_content, "text/csv")},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["total_rows"] == 3
    assert body["valid_rows"] == 2
    assert body["invalid_rows"] == 1
    confirmed = client.post(
        "/api/v1/imports/csv/confirm",
        headers=headers,
        json={"preview_id": body["preview_id"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["imported"] == 2
    assert confirmed.json()["rejected"][0]["row"] == 3

    preview_again = client.post(
        "/api/v1/imports/csv/preview",
        headers=headers,
        files={"file": ("transactions.csv", csv_content, "text/csv")},
    ).json()
    repeated = client.post(
        "/api/v1/imports/csv/confirm",
        headers=headers,
        json={"preview_id": preview_again["preview_id"]},
    )
    assert repeated.json()["imported"] == 0
    assert repeated.json()["duplicates_skipped"] == 2
    assert len(repeated.json()["rejected"]) == 1


def test_seed_persona_is_idempotent(client, db_engine):
    headers, user_id = auth(client)
    first = client.post("/api/v1/onboarding/demo", headers=headers, json={"persona": "ananya"})
    assert first.status_code == 201, first.text
    assert first.json()["transactions_ingested"] > 10
    with Session(db_engine) as db:
        count_before = db.scalar(select(func.count()).select_from(Transaction))
        second = seed_persona(db, UUID(user_id), "ananya")
        count_after = db.scalar(select(func.count()).select_from(Transaction))
    assert second["transactions_ingested"] == 0
    assert second["duplicates_skipped"] == first.json()["transactions_ingested"]
    assert count_after == count_before


def test_all_invalid_batch_returns_row_details(client):
    headers, _ = auth(client)
    response = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "transactions": [
                {
                    "account_id": "not-a-uuid",
                    "txn_date": str(date(2026, 9, 1)),
                    "amount": "0",
                    "direction": "sideways",
                    "raw_description": "",
                }
            ]
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"]["rows"][0]["row"] == 1
