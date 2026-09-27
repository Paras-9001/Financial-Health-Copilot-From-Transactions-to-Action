from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Account, Merchant, Transaction


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def duplicate_exists(self, account_id: UUID, dedup_hash: str) -> bool:
        return (
            self.db.scalar(
                select(Transaction.id).where(
                    Transaction.account_id == account_id, Transaction.dedup_hash == dedup_hash
                )
            )
            is not None
        )

    def create(self, **values) -> Transaction:
        transaction = Transaction(**values)
        self.db.add(transaction)
        self.db.flush()
        return transaction

    def get_owned(self, user_id: UUID, transaction_id: UUID) -> Transaction | None:
        return self.db.scalar(
            select(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(Transaction.id == transaction_id, Account.user_id == user_id)
        )

    def list_for_user(
        self,
        user_id: UUID,
        *,
        category_id: UUID | None = None,
        merchant: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Transaction], int]:
        query = (
            select(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.user_id == user_id)
        )
        if category_id:
            query = query.where(Transaction.category_id == category_id)
        if merchant:
            query = query.join(Merchant, Merchant.id == Transaction.merchant_id).where(
                func.lower(Merchant.normalized_name).contains(merchant.lower())
            )
        if start_date:
            query = query.where(Transaction.txn_date >= start_date)
        if end_date:
            query = query.where(Transaction.txn_date <= end_date)
        if min_amount is not None:
            query = query.where(Transaction.amount >= min_amount)
        if max_amount is not None:
            query = query.where(Transaction.amount <= max_amount)
        count = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = list(
            self.db.scalars(
                query.order_by(Transaction.txn_date.desc(), Transaction.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return rows, count
