from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["checking", "savings", "credit_card", "loan", "investment"]
    name: str = Field(min_length=1, max_length=100)
    balance: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Account name must not be blank")
        return value.strip()

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: str
    name: str
    balance: Decimal
    currency: str


class AccountListResponse(BaseModel):
    accounts: list[AccountResponse]
