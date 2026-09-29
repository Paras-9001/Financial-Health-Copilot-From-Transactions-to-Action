from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.repository import AnalyticsRepository
from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import current_user
from app.db.user import User
from app.forecast.service import generate_forecast
from app.recurring.service import detect_and_persist_recurring
from app.risks.repository import RiskRepository
from app.risks.schemas import RiskEventResponse, RisksListResponse
from app.risks.service import run_risk_engine

router = APIRouter(tags=["Risk Events"])


def _run_and_persist_risks(user: User, db: Session) -> list:
    """Run the full risk pipeline and persist results. Returns active risk events."""
    analytics = AnalyticsRepository(db)
    transactions = analytics.get_user_transactions(user.id)
    if not transactions:
        raise APIError(404, "no_data", "No transactions found for user")

    category_map = analytics.get_categories_map()
    detect_and_persist_recurring(db, user.id, transactions, category_map)
    recurring = analytics.get_recurring_transactions(user.id)

    forecast = generate_forecast(
        accounts=analytics.get_accounts(user.id),
        transactions=transactions,
        recurring=recurring,
        income_sources=analytics.get_income_sources(user.id),
        category_map=category_map,
        loans=analytics.get_loans(user.id),
    )

    as_of_date = max(txn.txn_date for txn in transactions)
    candidates = run_risk_engine(
        accounts=analytics.get_accounts(user.id),
        transactions=transactions,
        category_map=category_map,
        recurring=recurring,
        income_sources=analytics.get_income_sources(user.id),
        loans=analytics.get_loans(user.id),
        credit_cards=analytics.get_credit_cards(user.id),
        forecast=forecast,
        as_of_date=as_of_date,
        preferred_buffer_days=user.preferred_buffer_days,
    )

    risk_repo = RiskRepository(db)
    risk_repo.upsert_risks(user.id, candidates)
    db.commit()

    return risk_repo.get_active_risks(user.id)


@router.get("/risks", response_model=RisksListResponse)
def get_risks(
    status: str = Query(default="active"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Return risk events for the current user, re-running the risk engine on each call."""
    analytics = AnalyticsRepository(db)
    transactions = analytics.get_user_transactions(user.id)
    if not transactions:
        raise APIError(404, "no_data", "No transactions found for user")

    category_map = analytics.get_categories_map()
    detect_and_persist_recurring(db, user.id, transactions, category_map)
    recurring = analytics.get_recurring_transactions(user.id)

    forecast = generate_forecast(
        accounts=analytics.get_accounts(user.id),
        transactions=transactions,
        recurring=recurring,
        income_sources=analytics.get_income_sources(user.id),
        category_map=category_map,
        loans=analytics.get_loans(user.id),
    )

    as_of_date = max(txn.txn_date for txn in transactions)
    candidates = run_risk_engine(
        accounts=analytics.get_accounts(user.id),
        transactions=transactions,
        category_map=category_map,
        recurring=recurring,
        income_sources=analytics.get_income_sources(user.id),
        loans=analytics.get_loans(user.id),
        credit_cards=analytics.get_credit_cards(user.id),
        forecast=forecast,
        as_of_date=as_of_date,
        preferred_buffer_days=user.preferred_buffer_days,
    )

    risk_repo = RiskRepository(db)
    risk_repo.upsert_risks(user.id, candidates)
    db.commit()

    risk_events = risk_repo.get_all_risks(user.id, status=status if status != "all" else None)
    return RisksListResponse(
        risks=[
            RiskEventResponse(
                id=event.id,
                risk_type=event.risk_type,
                severity=event.severity,
                evidence={k: v for k, v in event.evidence.items() if k != "_dedup_key"},
                confidence=f"{event.confidence:.2f}",
                detected_at=event.detected_at,
                status=event.status,
            )
            for event in risk_events
        ]
    )
