from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class RecurringExpenseItem(BaseModel):
    id: UUID
    merchant: str
    amount: str
    amount_variance_pct: str | None
    frequency: str
    next_expected_date: date | None
    status: Literal["candidate", "confirmed"]
    confirmed_cycles: int


class RecurringExpenseResponse(BaseModel):
    recurring: list[RecurringExpenseItem]
