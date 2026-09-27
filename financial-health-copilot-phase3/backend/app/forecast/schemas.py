from datetime import date
from pydantic import BaseModel
from typing import List, Literal


class DailyProjection(BaseModel):
    date: date
    projected_balance: str
    lower_bound: str
    upper_bound: str


class ForecastResponse(BaseModel):
    daily_projection: List[DailyProjection]
    confidence: Literal["high", "medium", "low"]
    method: str
