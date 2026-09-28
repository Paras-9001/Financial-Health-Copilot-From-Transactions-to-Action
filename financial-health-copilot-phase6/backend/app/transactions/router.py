from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.categorization.service import remember_override
from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import current_user
from app.db.models import Category
from app.db.user import User
from app.transactions.repository import TransactionRepository
from app.transactions.schemas import (
    TransactionBatchRequest,
    TransactionCategoryUpdate,
    TransactionIngestResponse,
    TransactionListResponse,
    TransactionResponse,
)
from app.transactions.service import ingest_transactions

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    category_id: UUID | None = None,
    merchant: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise APIError(422, "validation_error", "start_date must not be after end_date")
    rows, total = TransactionRepository(db).list_for_user(
        user.id,
        category_id=category_id,
        merchant=merchant,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        page=page,
        page_size=page_size,
    )
    return {"transactions": rows, "total_count": total, "page": page, "page_size": page_size}


@router.post("", response_model=TransactionIngestResponse, status_code=201)
def create_transactions(
    data: TransactionBatchRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    result = ingest_transactions(db, user.id, data.transactions)
    if not result["ingested"] and not result["duplicates_skipped"] and result["rejected"]:
        raise APIError(
            422,
            "validation_error",
            "No transaction rows were valid.",
            {"rows": result["rejected"]},
        )
    return result


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction_category(
    transaction_id: UUID,
    data: TransactionCategoryUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repository = TransactionRepository(db)
    transaction = repository.get_owned(user.id, transaction_id)
    if transaction is None:
        raise APIError(404, "transaction_not_found", "Transaction was not found.")
    category = db.scalar(select(Category).where(Category.id == data.category_id))
    if category is None:
        raise APIError(404, "category_not_found", "Category was not found.")
    transaction.category_id = category.id
    transaction.is_manual_override = True
    remember_override(db, user.id, transaction.merchant_id, category.id)
    db.commit()
    db.refresh(transaction)
    return transaction
