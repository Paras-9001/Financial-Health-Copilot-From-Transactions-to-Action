from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, Merchant, MerchantCategoryOverride


class CategorizationRepository:
    def __init__(self, db: Session):
        self.db = db

    def categories_by_name(self) -> dict[str, Category]:
        return {category.name: category for category in self.db.scalars(select(Category))}

    def merchant_by_pattern(self, pattern: str) -> Merchant | None:
        return self.db.scalar(select(Merchant).where(Merchant.raw_pattern == pattern))

    def list_merchants(self) -> list[Merchant]:
        return list(self.db.scalars(select(Merchant).order_by(Merchant.raw_pattern)))

    def override(self, user_id: UUID, merchant_id: UUID) -> MerchantCategoryOverride | None:
        return self.db.scalar(
            select(MerchantCategoryOverride).where(
                MerchantCategoryOverride.user_id == user_id,
                MerchantCategoryOverride.merchant_id == merchant_id,
            )
        )
