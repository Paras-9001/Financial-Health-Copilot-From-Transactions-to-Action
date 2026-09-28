from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Intent(StrEnum):
    SPENDING = "spending"
    SAVINGS = "savings"
    DEBT = "debt"
    CASH_FLOW = "cash_flow"
    AFFORDABILITY = "affordability"
    RECOMMENDATION = "recommendation"
    WHAT_IF = "what_if"
    GENERAL = "general"
    UNCLEAR = "general/unclear"


class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


class Period(BaseModel):
    start_date: date
    end_date: date

    @field_validator("end_date")
    @classmethod
    def valid_range(cls, value: date, info):
        start = info.data.get("start_date")
        if start and value < start:
            raise ValueError("end_date must be on or after start_date")
        return value


class Claim(BaseModel):
    type: str = Field(pattern="^(fact|prediction|recommendation|assumption)$")
    label: str
    value: Any | None = None
    source: str
    confidence: str | None = None
    basis: str | None = None


class ToolCallRecord(BaseModel):
    tool: str
    args: dict[str, Any]
    status: str
    result_summary: str


class ChatResponse(BaseModel):
    answer_text: str
    intent: Intent
    facts: list[Claim] = Field(default_factory=list)
    predictions: list[Claim] = Field(default_factory=list)
    recommendations: list[Claim] = Field(default_factory=list)
    assumptions: list[Claim] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    provider: str = "deterministic"
    grounded: bool = True


class ChatSessionResponse(BaseModel):
    session_id: UUID
    title: str | None = None
    created_at: datetime


class ChatHistoryMessage(BaseModel):
    id: UUID
    role: str
    content: str
    structured_answer: ChatResponse | None = None
    created_at: datetime
