from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CashFlowForecast
from app.forecast.service import ForecastResult


class ForecastRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, user_id: UUID, result: ForecastResult) -> CashFlowForecast:
        row = CashFlowForecast(
            user_id=user_id,
            horizon_days=result.horizon_days,
            daily_projection=[
                {
                    "date": point.date.isoformat(),
                    "projected_balance": f"{point.projected_balance:.2f}",
                    "lower_bound": f"{point.lower_bound:.2f}",
                    "upper_bound": f"{point.upper_bound:.2f}",
                    "scheduled_inflow": f"{point.scheduled_inflow:.2f}",
                    "scheduled_outflow": f"{point.scheduled_outflow:.2f}",
                    "unscheduled_spend": f"{point.unscheduled_spend:.2f}",
                }
                for point in result.daily_projection
            ],
            method="rolling_average_v1",
            confidence=result.confidence,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def latest_for_user(self, user_id: UUID) -> CashFlowForecast | None:
        return self.db.scalar(
            select(CashFlowForecast)
            .where(CashFlowForecast.user_id == user_id)
            .order_by(CashFlowForecast.generated_at.desc())
            .limit(1)
        )
