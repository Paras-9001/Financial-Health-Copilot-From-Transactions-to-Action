from datetime import date
from typing import Literal

from pydantic import BaseModel


class DailyProjection(BaseModel):
    date: date
    projected_balance: str
    lower_bound: str
    upper_bound: str
    scheduled_inflow: str
    scheduled_outflow: str
    unscheduled_spend: str


class ForecastResponse(BaseModel):
    as_of_date: date
    horizon_days: int
    daily_projection: list[DailyProjection]
    confidence: Literal["high", "medium", "low"]
    method: Literal["rolling_average_v1"]
    history_days: int
    spending_cv: str
    recurring_coverage_pct: str
    assumptions: list[str]
