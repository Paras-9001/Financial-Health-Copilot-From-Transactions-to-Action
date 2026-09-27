from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.repository import AnalyticsRepository
from app.core.database import get_db
from app.core.security import current_user
from app.db.models import Merchant
from app.db.user import User
from app.recurring.schemas import RecurringExpenseResponse
from app.recurring.service import detect_and_persist_recurring

router = APIRouter(tags=["Recurring Expenses"])


@router.get("/recurring-expenses", response_model=RecurringExpenseResponse)
def get_recurring_expenses(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repository = AnalyticsRepository(db)
    transactions = repository.get_user_transactions(user.id)
    recurring = detect_and_persist_recurring(db, user.id, transactions, repository.get_categories_map())
    merchant_names = {
        merchant.id: merchant.normalized_name for merchant in db.scalars(select(Merchant)).all()
    }
    db.commit()
    recurring = sorted(
        recurring,
        key=lambda item: (item.next_expected_date or date.max, merchant_names.get(item.merchant_id, "")),
    )
    return RecurringExpenseResponse(
        recurring=[
            {
                "id": item.id,
                "merchant": merchant_names.get(item.merchant_id, "Unknown merchant"),
                "amount": f"{item.expected_amount:.2f}",
                "amount_variance_pct": (
                    f"{item.amount_variance_pct:.2f}" if item.amount_variance_pct is not None else None
                ),
                "frequency": item.frequency,
                "next_expected_date": item.next_expected_date,
                "status": item.status,
                "confirmed_cycles": item.confirmed_cycles,
            }
            for item in recurring
        ]
    )
