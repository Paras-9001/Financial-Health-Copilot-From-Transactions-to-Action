from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.repository import AnalyticsRepository
from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import current_user
from app.db.user import User
from app.forecast.service import generate_forecast
from app.recommendations.repository import RecommendationRepository
from app.recommendations.schemas import (
    RecommendationHistoryItem,
    RecommendationHistoryResponse,
    RecommendationResponse,
    RecommendationsListResponse,
)
from app.recommendations.service import generate_recommendations
from app.recurring.service import detect_and_persist_recurring
from app.risks.repository import RiskRepository
from app.risks.service import run_risk_engine

router = APIRouter(tags=["Recommendations"])


def _run_recommendation_pipeline(user: User, db: Session) -> list:
    """Run the complete risk -> recommendation pipeline."""
    analytics = AnalyticsRepository(db)
    transactions = analytics.get_user_transactions(user.id)
    if not transactions:
        raise APIError(404, "no_data", "No transactions found for user")

    category_map = analytics.get_categories_map()
    detect_and_persist_recurring(db, user.id, transactions, category_map)
    recurring = analytics.get_recurring_transactions(user.id)
    accounts = analytics.get_accounts(user.id)
    income_sources = analytics.get_income_sources(user.id)
    loans = analytics.get_loans(user.id)
    credit_cards = analytics.get_credit_cards(user.id)

    forecast = generate_forecast(
        accounts=accounts,
        transactions=transactions,
        recurring=recurring,
        income_sources=income_sources,
        category_map=category_map,
        loans=loans,
    )

    as_of_date = max(txn.txn_date for txn in transactions)
    candidates = run_risk_engine(
        accounts=accounts,
        transactions=transactions,
        category_map=category_map,
        recurring=recurring,
        income_sources=income_sources,
        loans=loans,
        credit_cards=credit_cards,
        forecast=forecast,
        as_of_date=as_of_date,
        preferred_buffer_days=user.preferred_buffer_days,
    )

    risk_repo = RiskRepository(db)
    risk_repo.upsert_risks(user.id, candidates)
    db.flush()

    active_risks = risk_repo.get_active_risks(user.id)
    reco_candidates = generate_recommendations(
        risk_events=active_risks,
        accounts=accounts,
        transactions=transactions,
        category_map=category_map,
        recurring=recurring,
        income_sources=income_sources,
        loans=loans,
        credit_cards=credit_cards,
        history_days=forecast.history_days,
    )

    reco_repo = RecommendationRepository(db)
    reco_repo.upsert_recommendations(user.id, reco_candidates)
    db.commit()
    return reco_repo.get_active(user.id)


@router.get("/recommendations", response_model=RecommendationsListResponse)
def get_recommendations(
    status: str = Query(default="active"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Return recommendations for the current user, re-running the full pipeline on each call."""
    recommendations = _run_recommendation_pipeline(user, db)
    reco_repo = RecommendationRepository(db)
    if status != "active":
        all_recos = reco_repo.get_all(user.id, status=status if status != "all" else None)
    else:
        all_recos = recommendations

    return RecommendationsListResponse(
        recommendations=[
            RecommendationResponse(
                id=r.id,
                risk_event_id=r.risk_event_id,
                title=r.title,
                reason=r.reason,
                evidence=r.evidence,
                action=r.action,
                expected_impact=r.expected_impact,
                confidence=f"{r.confidence:.2f}",
                priority=r.priority,
                assumptions=r.assumptions,
                generated_at=r.generated_at,
                status=r.status,
            )
            for r in all_recos
        ]
    )


@router.get("/recommendations/{id}/history", response_model=RecommendationHistoryResponse)
def get_recommendation_history(
    id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Return historical timeline for a recommendation."""
    reco_repo = RecommendationRepository(db)
    timeline = reco_repo.get_history(user.id, id)
    if not timeline:
        raise APIError(404, "recommendation_not_found", "Recommendation not found")
    return RecommendationHistoryResponse(
        timeline=[
            RecommendationHistoryItem(
                timestamp=item["timestamp"],
                status=item["status"],
                expected_impact=item["expected_impact"],
            )
            for item in timeline
        ]
    )
