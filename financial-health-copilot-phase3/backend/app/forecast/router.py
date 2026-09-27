from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from app.core.database import get_db
from app.core.security import current_user
from app.db.user import User
from app.analytics.repository import AnalyticsRepository
from app.forecast.schemas import ForecastResponse
from app.forecast.service import generate_forecast

router = APIRouter(tags=["Cash-Flow Forecast"])

@router.get("/cash-flow/forecast", response_model=ForecastResponse)
def get_cash_flow_forecast(
    horizon_days: int = Query(default=30, le=90),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repo = AnalyticsRepository(db)
    
    accounts = repo.get_accounts(user.id)
    txns = repo.get_user_transactions(user.id)
    recurring = repo.get_recurring_transactions(user.id)
    income_sources = repo.get_income_sources(user.id)
    cat_map = repo.get_categories_map()
    loans = repo.get_loans(user.id)
    
    response = generate_forecast(
        accounts=accounts,
        txns=txns,
        recurring=recurring,
        income_sources=income_sources,
        cat_map=cat_map,
        loans=loans,
        horizon_days=horizon_days
    )
    
    return response
