from sqlalchemy import select
from sqlalchemy.orm import Session

from app.categorization.service import ensure_taxonomy
from app.db.models import Category


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Category]:
        ensure_taxonomy(self.db)
        return list(self.db.scalars(select(Category).order_by(Category.name)))
