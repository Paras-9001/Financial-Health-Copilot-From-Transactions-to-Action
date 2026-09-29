from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Recommendation, RecommendationImpact
from app.recommendations.service import RecommendationCandidate


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active(self, user_id: UUID) -> list[Recommendation]:
        stmt = (
            select(Recommendation)
            .where(Recommendation.user_id == user_id, Recommendation.status == "active")
            .order_by(Recommendation.generated_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_all(self, user_id: UUID, status: str | None = None) -> list[Recommendation]:
        stmt = select(Recommendation).where(Recommendation.user_id == user_id)
        if status:
            stmt = stmt.where(Recommendation.status == status)
        stmt = stmt.order_by(Recommendation.generated_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, user_id: UUID, reco_id: UUID) -> Recommendation | None:
        return self.db.scalar(
            select(Recommendation).where(Recommendation.user_id == user_id, Recommendation.id == reco_id)
        )

    def upsert_recommendations(
        self, user_id: UUID, candidates: list[RecommendationCandidate]
    ) -> list[Recommendation]:
        """Update stable recommendations and supersede actions no longer generated."""
        active = self.get_active(user_id)
        active_by_key = {
            self._identity(existing.risk_event_id, existing.action): existing for existing in active
        }
        candidate_keys = {self._identity(c.risk_event_id, c.action) for c in candidates}
        for existing in active:
            if self._identity(existing.risk_event_id, existing.action) not in candidate_keys:
                existing.status = "superseded"

        current_records: list[Recommendation] = []
        for c in candidates:
            key = self._identity(c.risk_event_id, c.action)
            existing = active_by_key.get(key)
            if existing is not None:
                existing.title = c.title
                existing.reason = c.reason
                existing.evidence = c.evidence
                existing.action = c.action
                existing.expected_impact = c.expected_impact
                existing.confidence = c.confidence
                existing.priority = c.priority
                existing.assumptions = c.assumptions
                current_records.append(existing)
                continue
            rec = Recommendation(
                user_id=user_id,
                risk_event_id=c.risk_event_id,
                title=c.title,
                reason=c.reason,
                evidence=c.evidence,
                action=c.action,
                expected_impact=c.expected_impact,
                confidence=c.confidence,
                priority=c.priority,
                assumptions=c.assumptions,
                status="active",
            )
            self.db.add(rec)
            current_records.append(rec)

        self.db.flush()
        return current_records

    @staticmethod
    def _identity(risk_event_id: UUID | None, action: dict) -> tuple:
        """Stable identity for a recommendation across recalculations."""
        return (
            str(risk_event_id) if risk_event_id else None,
            action.get("type"),
            action.get("category"),
            action.get("loan_id"),
            action.get("account_id"),
            action.get("recurring_id"),
        )

    def get_history(self, user_id: UUID, reco_id: UUID) -> list[dict]:
        """Return timeline of changes for a recommendation (and previously related ones)."""
        rec = self.get_by_id(user_id, reco_id)
        if rec is None:
            return []
        identity = self._identity(rec.risk_event_id, rec.action)
        related = [
            item
            for item in self.get_all(user_id)
            if self._identity(item.risk_event_id, item.action) == identity
        ]
        return [
            {
                "timestamp": item.generated_at.isoformat(),
                "status": item.status,
                "expected_impact": item.expected_impact,
            }
            for item in related
        ]

    def save_impact(
        self,
        recommendation_id: UUID,
        baseline: dict,
        proposed: dict,
        delta_summary: dict,
    ) -> RecommendationImpact:
        impact = RecommendationImpact(
            recommendation_id=recommendation_id,
            baseline=baseline,
            proposed=proposed,
            delta_summary=delta_summary,
        )
        self.db.add(impact)
        self.db.flush()
        return impact
