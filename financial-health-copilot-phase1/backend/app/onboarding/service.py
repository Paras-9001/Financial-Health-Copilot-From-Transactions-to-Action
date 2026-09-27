from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.repository import AccountRepository
from app.credit_cards.repository import CreditCardRepository
from app.db.models import Investment, Loan
from app.income_sources.repository import IncomeSourceRepository
from app.loans.repository import LoanRepository
from app.onboarding.personas import PERSONAS
from app.transactions.service import ingest_transactions


def has_financial_data(db: Session, user_id: UUID) -> bool:
    account = AccountRepository(db).list_for_user(user_id)
    return bool(account)


def seed_persona(db: Session, user_id: UUID, persona_key: str) -> dict:
    persona = PERSONAS[persona_key]
    account_repository = AccountRepository(db)
    account_map = {}
    created = 0
    for account_data in persona["accounts"]:
        account = account_repository.get_by_name(user_id, account_data["name"])
        if account is None:
            account = account_repository.create(
                user_id,
                type=account_data["type"],
                name=account_data["name"],
                balance=Decimal(account_data["balance"]),
                currency="INR",
            )
            created += 1
        else:
            account.balance = Decimal(account_data["balance"])
        account_map[account_data["key"]] = account

    income_repo = IncomeSourceRepository(db)
    income = persona["income"]
    source = income_repo.get_by_name(user_id, income["name"])
    if source is None:
        income_repo.create(user_id, **income)
    else:
        for key, value in income.items():
            setattr(source, key, value)

    if persona.get("loan"):
        loan_data = dict(persona["loan"])
        account = account_map[loan_data.pop("account_key")]
        loan = db.scalar(select(Loan).where(Loan.user_id == user_id, Loan.account_id == account.id))
        values = {
            key: Decimal(value) if isinstance(value, str) else value for key, value in loan_data.items()
        }
        if loan is None:
            LoanRepository(db).create(user_id, account_id=account.id, **values)
        else:
            for key, value in values.items():
                setattr(loan, key, value)

    if persona.get("card"):
        card_data = dict(persona["card"])
        account = account_map[card_data.pop("account_key")]
        values = {
            key: Decimal(value) if isinstance(value, str) else value for key, value in card_data.items()
        }
        card_repo = CreditCardRepository(db)
        card = card_repo.get_by_account(account.id)
        if card is None:
            card_repo.create(account_id=account.id, **values)
        else:
            for key, value in values.items():
                setattr(card, key, value)

    if persona.get("investment"):
        investment_data = dict(persona["investment"])
        account = account_map[investment_data.pop("account_key")]
        investment = db.scalar(select(Investment).where(Investment.account_id == account.id))
        values = {
            key: Decimal(value) if key == "current_value" else value for key, value in investment_data.items()
        }
        if investment is None:
            db.add(Investment(account_id=account.id, **values))
        else:
            for key, value in values.items():
                setattr(investment, key, value)

    db.flush()
    checking = account_map["checking"]
    transaction_rows = [
        {
            "account_id": checking.id,
            "txn_date": txn_date,
            "amount": amount,
            "direction": direction,
            "raw_description": description,
        }
        for txn_date, amount, direction, description in persona["transactions"]
    ]
    transaction_result = ingest_transactions(db, user_id, transaction_rows)
    return {
        "persona": persona_key,
        "accounts_created": created,
        "transactions_ingested": transaction_result["ingested"],
        "duplicates_skipped": transaction_result["duplicates_skipped"],
        "loans": int(bool(persona.get("loan"))),
        "credit_cards": int(bool(persona.get("card"))),
        "income_sources": 1,
    }
