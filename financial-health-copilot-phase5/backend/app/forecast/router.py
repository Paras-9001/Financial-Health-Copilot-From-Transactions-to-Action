from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.repository import AnalyticsRepository
from app.core import config
from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import current_user
from app.db.user import User
from app.forecast.repository import ForecastRepository
from app.forecast.schemas import ForecastResponse
from app.forecast.service import ForecastResult, generate_forecast
from app.recurring.service import detect_and_persist_recurring

router = APIRouter(tags=["Cash-Flow Forecast"])


def _response(result: ForecastResult) -> ForecastResponse:
    return ForecastResponse(
        as_of_date=result.as_of_date,
        horizon_days=result.horizon_days,
        daily_projection=[
            {
                "date": point.date,
                "projected_balance": f"{point.projected_balance:.2f}",
                "lower_bound": f"{point.lower_bound:.2f}",
                "upper_bound": f"{point.upper_bound:.2f}",
                "scheduled_inflow": f"{point.scheduled_inflow:.2f}",
                "scheduled_outflow": f"{point.scheduled_outflow:.2f}",
                "unscheduled_spend": f"{point.unscheduled_spend:.2f}",
            }
            for point in result.daily_projection
        ],
        confidence=result.confidence,
        method="rolling_average_v1",
        history_days=result.history_days,
        spending_cv=f"{result.spending_cv:.2f}",
        recurring_coverage_pct=f"{result.recurring_coverage_pct:.2f}",
        assumptions=[
            "Known recurring expenses, income sources, and loan installments continue on schedule.",
            (
                "Unscheduled variable and discretionary spending follows a trailing daily average "
                f"with a {result.trend_factor:.2f} trend multiplier."
            ),
            "Pending transactions and irregular future income are not included.",
        ],
    )


@router.get("/cash-flow/forecast", response_model=ForecastResponse)
def get_cash_flow_forecast(
    horizon_days: int = Query(
        default=config.FORECAST_HORIZON_DEFAULT_DAYS,
        ge=1,
        le=config.FORECAST_HORIZON_MAX_DAYS,
    ),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    analytics = AnalyticsRepository(db)
    transactions = analytics.get_user_transactions(user.id)
    if not transactions:
        raise APIError(404, "no_data", "No transactions found for user")

    category_map = analytics.get_categories_map()
    detect_and_persist_recurring(db, user.id, transactions, category_map)
    recurring = analytics.get_recurring_transactions(user.id)
    result = generate_forecast(
        accounts=analytics.get_accounts(user.id),
        transactions=transactions,
        recurring=recurring,
        income_sources=analytics.get_income_sources(user.id),
        category_map=category_map,
        loans=analytics.get_loans(user.id),
        horizon_days=horizon_days,
    )
    ForecastRepository(db).save(user.id, result)
    db.commit()
    return _response(result)
