import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.accounts.repository import AccountRepository
from app.categorization.service import categorize
from app.core import config
from app.transactions.repository import TransactionRepository
from app.transactions.schemas import TransactionCreate


def dedup_hash(account_id: UUID, txn_date: date, amount: Decimal, raw_description: str) -> str:
    canonical_amount = abs(amount).quantize(Decimal("0.01"))
    payload = f"{account_id}|{txn_date.isoformat()}|{canonical_amount}|{raw_description.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validation_errors(exc: ValidationError) -> list[dict[str, str]]:
    return [{"field": ".".join(map(str, error["loc"])), "message": error["msg"]} for error in exc.errors()]


def _history_warning(txn_date: date) -> str | None:
    today = datetime.now(UTC).date()
    if txn_date > today:
        return "future_date"
    cutoff = today - timedelta(days=config.SUPPORTED_HISTORY_MONTHS * 31)
    if txn_date < cutoff:
        return "older_than_supported_history"
    return None


def ingest_transactions(
    db: Session,
    user_id: UUID,
    rows: list[dict[str, Any]],
    *,
    update_balances: bool = False,
) -> dict[str, Any]:
    accounts = AccountRepository(db)
    transactions = TransactionRepository(db)
    ingested = 0
    duplicates = 0
    rejected: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for index, raw in enumerate(rows, start=1):
        try:
            data = TransactionCreate.model_validate(raw)
        except ValidationError as exc:
            rejected.append({"row": index, "errors": _validation_errors(exc)})
            continue
        account = accounts.get_owned(user_id, data.account_id)
        if account is None:
            rejected.append(
                {
                    "row": index,
                    "errors": [{"field": "account_id", "message": "Account was not found"}],
                }
            )
            continue
        row_hash = dedup_hash(data.account_id, data.txn_date, data.amount, data.raw_description)
        if transactions.duplicate_exists(data.account_id, row_hash):
            duplicates += 1
            continue
        result = categorize(db, user_id, data.raw_description)
        transactions.create(
            account_id=data.account_id,
            txn_date=data.txn_date,
            amount=data.amount,
            direction=data.direction,
            raw_description=data.raw_description,
            merchant_id=result.merchant_id,
            category_id=result.category_id,
            dedup_hash=row_hash,
            is_manual_override=False,
        )
        if update_balances:
            if account.type in ("checking", "savings"):
                account.balance += data.amount if data.direction == "credit" else -data.amount
            elif account.type == "credit_card":
                account.balance += data.amount if data.direction == "debit" else -data.amount
        ingested += 1
        warning = _history_warning(data.txn_date)
        if warning:
            warnings.append({"row": index, "code": warning})
    if ingested or duplicates:
        db.commit()
    else:
        db.rollback()
    return {
        "ingested": ingested,
        "duplicates_skipped": duplicates,
        "rejected": rejected,
        "warnings": warnings,
        "recalculation_triggered": bool(ingested),
    }
