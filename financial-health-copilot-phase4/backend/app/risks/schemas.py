from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EvidenceSchema(BaseModel):
    model_config = {"extra": "allow"}


class RiskEventResponse(BaseModel):
    id: UUID
    risk_type: str
    severity: str
    evidence: dict
    confidence: str
    detected_at: datetime
    status: str


class RisksListResponse(BaseModel):
    risks: list[RiskEventResponse]
