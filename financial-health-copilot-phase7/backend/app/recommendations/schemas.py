from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EvidenceItem(BaseModel):
    type: str
    label: str
    value: str
    confidence: str | None = None


class ActionSchema(BaseModel):
    model_config = {"extra": "allow"}
    type: str


class ImpactBufferDays(BaseModel):
    before: float
    after: float


class ExpectedImpactSchema(BaseModel):
    model_config = {"extra": "allow"}
    buffer_days: ImpactBufferDays | None = None


class RecommendationResponse(BaseModel):
    id: UUID
    risk_event_id: UUID | None
    title: str
    reason: str
    evidence: list[dict]
    action: dict
    expected_impact: dict
    confidence: str
    priority: str
    assumptions: list[str]
    generated_at: datetime
    status: str


class RecommendationsListResponse(BaseModel):
    recommendations: list[RecommendationResponse]


class RecommendationHistoryItem(BaseModel):
    timestamp: str
    status: str
    expected_impact: dict


class RecommendationHistoryResponse(BaseModel):
    timeline: list[RecommendationHistoryItem]
