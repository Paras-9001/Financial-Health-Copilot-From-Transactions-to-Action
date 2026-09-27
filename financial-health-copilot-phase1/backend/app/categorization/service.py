import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.categorization.repository import CategorizationRepository
from app.db.models import Category, Merchant, MerchantCategoryOverride

CATEGORY_TAXONOMY = {
    "Rent": "fixed",
    "Debt Payment": "fixed",
    "Subscriptions": "fixed",
    "Groceries": "variable",
    "Utilities": "variable",
    "Transport": "variable",
    "Healthcare": "variable",
    "Dining": "discretionary",
    "Shopping": "discretionary",
    "Entertainment": "discretionary",
    "Income": "income",
    "Transfer": "transfer",
    "Other": "variable",
    "Uncategorized": "variable",
}

MERCHANT_RULES = (
    ("SWIGGY", "Swiggy", "Dining"),
    ("ZOMATO", "Zomato", "Dining"),
    ("BIGBASKET", "BigBasket", "Groceries"),
    ("DMART", "DMart", "Groceries"),
    ("NETFLIX", "Netflix", "Subscriptions"),
    ("SPOTIFY", "Spotify", "Subscriptions"),
    ("GYM", "Gym", "Subscriptions"),
    ("AMAZON", "Amazon", "Shopping"),
    ("FLIPKART", "Flipkart", "Shopping"),
    ("UBER", "Uber", "Transport"),
    ("OLA", "Ola", "Transport"),
    ("ELECTRICITY", "Electricity Board", "Utilities"),
    ("WATER BILL", "Water Bill", "Utilities"),
    ("RENT", "Rent", "Rent"),
    ("EMI", "Loan EMI", "Debt Payment"),
    ("CC PAYMENT", "Credit Card Payment", "Debt Payment"),
    ("SALARY", "Salary", "Income"),
    ("CLIENT", "Client Payment", "Income"),
    ("MUTUAL FUND", "Mutual Fund", "Transfer"),
)


@dataclass(frozen=True)
class CategorizationResult:
    merchant_id: UUID | None
    category_id: UUID
    normalized_description: str
    confidence: str


def normalize_description(raw: str) -> str:
    value = re.sub(r"\s+", " ", raw.strip().upper())
    value = re.sub(r"(?:[*#/_-]?(?:ORDER|TXN|REF)?[A-Z0-9]{4,})$", "", value).strip(" *#/_-")
    return value or raw.strip().upper()


def ensure_taxonomy(db: Session) -> dict[str, Category]:
    repository = CategorizationRepository(db)
    existing = repository.categories_by_name()
    for name, category_type in CATEGORY_TAXONOMY.items():
        if name not in existing:
            category = Category(name=name, type=category_type)
            db.add(category)
            db.flush()
            existing[name] = category
    for pattern, normalized_name, category_name in MERCHANT_RULES:
        merchant = repository.merchant_by_pattern(pattern)
        if merchant is None:
            db.add(
                Merchant(
                    raw_pattern=pattern,
                    normalized_name=normalized_name,
                    default_category_id=existing[category_name].id,
                )
            )
    db.flush()
    return existing


def categorize(db: Session, user_id: UUID, raw_description: str) -> CategorizationResult:
    categories = ensure_taxonomy(db)
    normalized = normalize_description(raw_description)
    repository = CategorizationRepository(db)
    merchant = None
    for candidate in repository.list_merchants():
        if candidate.raw_pattern.upper() in normalized:
            merchant = candidate
            break
    if merchant is None:
        return CategorizationResult(None, categories["Uncategorized"].id, normalized, "low")
    override = repository.override(user_id, merchant.id)
    return CategorizationResult(
        merchant.id,
        override.category_id if override else merchant.default_category_id,
        normalized,
        "high" if override or merchant.default_category_id else "low",
    )


def remember_override(db: Session, user_id: UUID, merchant_id: UUID | None, category_id: UUID) -> None:
    if merchant_id is None:
        return
    existing = CategorizationRepository(db).override(user_id, merchant_id)
    if existing:
        existing.category_id = category_id
    else:
        db.add(MerchantCategoryOverride(user_id=user_id, merchant_id=merchant_id, category_id=category_id))
