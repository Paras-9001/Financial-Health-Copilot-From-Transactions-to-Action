from typing import Literal

from pydantic import BaseModel, ConfigDict


class DemoSeedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    persona: Literal["ananya", "rohit", "meera"]


class DemoSeedResponse(BaseModel):
    persona: str
    accounts_created: int
    transactions_ingested: int
    duplicates_skipped: int
    loans: int
    credit_cards: int
    income_sources: int


class PersonaResponse(BaseModel):
    key: str
    name: str
    description: str
