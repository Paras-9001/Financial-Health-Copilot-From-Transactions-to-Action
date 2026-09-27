from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncomeSourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    frequency: Literal["monthly", "biweekly", "irregular"]
    is_variable: bool = False
    last_received_date: date | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Income source name must not be blank")
        return value.strip()


class IncomeSourceResponse(IncomeSourceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class IncomeSourceListResponse(BaseModel):
    income_sources: list[IncomeSourceResponse]
