from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Account


class AccountRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: UUID) -> list[Account]:
        return list(
            self.db.scalars(select(Account).where(Account.user_id == user_id).order_by(Account.created_at))
        )

    def get_owned(self, user_id: UUID, account_id: UUID) -> Account | None:
        return self.db.scalar(select(Account).where(Account.id == account_id, Account.user_id == user_id))

    def get_by_name(self, user_id: UUID, name: str) -> Account | None:
        return self.db.scalar(
            select(Account).where(
                Account.user_id == user_id,
                func.lower(Account.name) == name.strip().lower(),
            )
        )

    def create(self, user_id: UUID, **values) -> Account:
        account = Account(user_id=user_id, **values)
        self.db.add(account)
        self.db.flush()
        return account

    def get_or_create_checking(self, user_id: UUID, name: str) -> Account:
        existing = self.get_by_name(user_id, name)
        if existing:
            return existing
        return self.create(user_id, type="checking", name=name.strip(), balance=0, currency="INR")
