from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import RiskEvent
from app.risks.service import RiskCandidate


class RiskRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_risks(self, user_id: UUID) -> list[RiskEvent]:
        stmt = (
            select(RiskEvent)
            .where(RiskEvent.user_id == user_id, RiskEvent.status == "active")
            .order_by(RiskEvent.detected_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_all_risks(self, user_id: UUID, status: str | None = None) -> list[RiskEvent]:
        stmt = select(RiskEvent).where(RiskEvent.user_id == user_id)
        if status:
            stmt = stmt.where(RiskEvent.status == status)
        stmt = stmt.order_by(RiskEvent.detected_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_risk_by_id(self, user_id: UUID, risk_id: UUID) -> RiskEvent | None:
        return self.db.scalar(select(RiskEvent).where(RiskEvent.user_id == user_id, RiskEvent.id == risk_id))

    def upsert_risks(self, user_id: UUID, candidates: list[RiskCandidate]) -> list[RiskEvent]:
        """Persist new risks; resolve risks whose triggering condition no longer holds."""
        # Resolve existing active risks that are no longer triggered
        active = self.get_active_risks(user_id)
        current_keys = {c.dedup_key for c in candidates}
        for existing in active:
            existing_key = existing.evidence.get("_dedup_key", existing.risk_type)
            if existing_key not in current_keys:
                existing.status = "resolved"
                existing.resolved_at = datetime.now(timezone.utc)

        # Create new risk events for newly detected candidates
        existing_by_key = {
            r.evidence.get("_dedup_key", r.risk_type): r for r in active if r.status == "active"
        }
        new_events: list[RiskEvent] = []
        for candidate in candidates:
            evidence_with_key = dict(candidate.evidence)
            evidence_with_key["_dedup_key"] = candidate.dedup_key
            existing = existing_by_key.get(candidate.dedup_key)
            if existing is not None:
                existing.severity = candidate.severity
                existing.evidence = evidence_with_key
                existing.confidence = candidate.confidence
            else:
                event = RiskEvent(
                    user_id=user_id,
                    risk_type=candidate.risk_type,
                    severity=candidate.severity,
                    evidence=evidence_with_key,
                    confidence=candidate.confidence,
                    status="active",
                )
                self.db.add(event)
                new_events.append(event)

        self.db.flush()
        return new_events
