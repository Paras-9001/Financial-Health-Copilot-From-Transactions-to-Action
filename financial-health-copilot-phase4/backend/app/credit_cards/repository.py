from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Account, CreditCard


class CreditCardRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: UUID) -> list[CreditCard]:
        return list(
            self.db.scalars(
                select(CreditCard)
                .join(Account, Account.id == CreditCard.account_id)
                .where(Account.user_id == user_id)
            )
        )

    def get_by_account(self, account_id: UUID) -> CreditCard | None:
        return self.db.scalar(select(CreditCard).where(CreditCard.account_id == account_id))

    def create(self, **values) -> CreditCard:
        card = CreditCard(**values)
        self.db.add(card)
        self.db.flush()
        return card
