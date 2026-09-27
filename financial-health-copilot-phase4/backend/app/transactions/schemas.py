from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: UUID
    txn_date: date
    amount: Decimal = Field(max_digits=14, decimal_places=2)
    direction: Literal["debit", "credit"]
    raw_description: str = Field(min_length=1, max_length=500)

    @field_validator("amount")
    @classmethod
    def nonzero_amount(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("Amount must not be zero")
        return abs(value)

    @field_validator("raw_description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Description must not be blank")
        return value.strip()


class TransactionBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transactions: list[dict[str, Any]] = Field(min_length=1, max_length=5000)


class RejectedRow(BaseModel):
    row: int
    errors: list[dict[str, str]]


class TransactionIngestResponse(BaseModel):
    ingested: int
    duplicates_skipped: int
    rejected: list[RejectedRow]
    warnings: list[dict[str, Any]]
    recalculation_triggered: bool


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    account_id: UUID
    txn_date: date
    amount: Decimal
    direction: str
    raw_description: str
    merchant_id: UUID | None
    category_id: UUID | None
    is_manual_override: bool
    created_at: datetime


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total_count: int
    page: int
    page_size: int


class TransactionCategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category_id: UUID
