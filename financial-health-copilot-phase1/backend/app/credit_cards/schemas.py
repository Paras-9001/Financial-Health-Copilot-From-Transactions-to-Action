from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreditCardCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: UUID
    credit_limit: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    current_balance: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    statement_date: int = Field(ge=1, le=31)
    minimum_due: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    apr: Decimal | None = Field(default=None, ge=0, max_digits=5, decimal_places=2)


class CreditCardResponse(CreditCardCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class CreditCardListResponse(BaseModel):
    credit_cards: list[CreditCardResponse]
