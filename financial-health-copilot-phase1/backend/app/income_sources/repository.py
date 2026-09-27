from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import IncomeSource


class IncomeSourceRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: UUID) -> list[IncomeSource]:
        return list(self.db.scalars(select(IncomeSource).where(IncomeSource.user_id == user_id)))

    def get_by_name(self, user_id: UUID, name: str) -> IncomeSource | None:
        return self.db.scalar(
            select(IncomeSource).where(
                IncomeSource.user_id == user_id,
                func.lower(IncomeSource.name) == name.strip().lower(),
            )
        )

    def create(self, user_id: UUID, **values) -> IncomeSource:
        source = IncomeSource(user_id=user_id, **values)
        self.db.add(source)
        self.db.flush()
        return source
