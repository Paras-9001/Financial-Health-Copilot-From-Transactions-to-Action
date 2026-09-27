from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Loan


class LoanRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: UUID) -> list[Loan]:
        return list(self.db.scalars(select(Loan).where(Loan.user_id == user_id)))

    def create(self, user_id: UUID, **values) -> Loan:
        loan = Loan(user_id=user_id, **values)
        self.db.add(loan)
        self.db.flush()
        return loan
