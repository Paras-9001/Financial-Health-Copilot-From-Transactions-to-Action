from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: UUID | None = None
    principal: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    interest_rate: Decimal = Field(ge=0, max_digits=5, decimal_places=2)
    term_months: int = Field(gt=0, le=600)
    start_date: date
    monthly_installment: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    outstanding_balance: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class LoanResponse(LoanCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class LoanListResponse(BaseModel):
    loans: list[LoanResponse]
