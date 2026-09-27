from datetime import date

from pydantic import BaseModel, Field, field_validator


class SimulateRequest(BaseModel):
    action_type: str
    params: dict
    horizon_days: int = Field(default=90, ge=1, le=180)

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        valid = {
            "reduce_spending",
            "increase_savings",
            "extra_debt_payment",
            "delay_purchase",
            "modify_recurring",
            "change_income",
        }
        if v not in valid:
            raise ValueError(f"action_type must be one of: {', '.join(sorted(valid))}")
        return v


class ForecastSeriesPoint(BaseModel):
    date: str
    balance: str


class SimulateSummary(BaseModel):
    model_config = {"extra": "allow"}
    cash_buffer_days_min: str | None = None
    month_end_balance: str | None = None
    loan_payoff_months: int | None = None
    total_interest_remaining: str | None = None
    confidence: str


class SimulateResponse(BaseModel):
    action: dict
    baseline: dict
    proposed: dict
    delta: dict
    confidence: str
    trade_off_note: str


class AffordabilityRequest(BaseModel):
    amount: str
    target_date: date


class AffordabilityResponse(BaseModel):
    verdict: str
    resulting_buffer_days: str
    confidence: str
    reasoning_basis: list[str]
