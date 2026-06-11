"""Human approval gate — no CFO recommendation executes without explicit approval."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cfo.types import CFORecommendation, RecommendationStatus
from backend.models.cfo import CFORecommendationRecord


class CFOApprovalGate:
    """All AI CFO actions pass through human approval before execution."""

    DEFAULT_EXPIRY_HOURS = 168  # 7 days

    def __init__(self, db: AsyncSession):
        self.db = db

    async def submit(
        self,
        tenant_id: UUID,
        user_id: UUID,
        recommendation: CFORecommendation,
    ) -> CFORecommendationRecord:
        record = CFORecommendationRecord(
            tenant_id=tenant_id,
            capability=recommendation.capability.value,
            title=recommendation.title,
            description=recommendation.description,
            rationale=recommendation.rationale,
            priority=recommendation.priority.value,
            confidence=recommendation.confidence,
            suggested_action=recommendation.suggested_action,
            impact_estimate=recommendation.impact_estimate,
            data_sources=recommendation.data_sources,
            status=RecommendationStatus.PENDING_APPROVAL.value,
            requires_approval=recommendation.requires_approval,
            submitted_by=user_id,
            expires_at=datetime.now(UTC) + timedelta(hours=self.DEFAULT_EXPIRY_HOURS),
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def approve(
        self,
        tenant_id: UUID,
        recommendation_id: UUID,
        reviewer_id: UUID,
        notes: str | None = None,
    ) -> dict[str, Any]:
        record = await self._get(tenant_id, recommendation_id)
        if not record:
            return {"success": False, "error": "Recommendation not found"}
        if record.status != RecommendationStatus.PENDING_APPROVAL.value:
            return {"success": False, "error": f"Cannot approve — status is {record.status}"}

        record.status = RecommendationStatus.APPROVED.value
        record.reviewed_by = reviewer_id
        record.reviewed_at = datetime.now(UTC)
        record.review_notes = notes
        await self.db.flush()
        return {"success": True, "id": str(record.id), "status": record.status}

    async def reject(
        self,
        tenant_id: UUID,
        recommendation_id: UUID,
        reviewer_id: UUID,
        notes: str | None = None,
    ) -> dict[str, Any]:
        record = await self._get(tenant_id, recommendation_id)
        if not record:
            return {"success": False, "error": "Recommendation not found"}
        if record.status != RecommendationStatus.PENDING_APPROVAL.value:
            return {"success": False, "error": f"Cannot reject — status is {record.status}"}

        record.status = RecommendationStatus.REJECTED.value
        record.reviewed_by = reviewer_id
        record.reviewed_at = datetime.now(UTC)
        record.review_notes = notes
        await self.db.flush()
        return {"success": True, "id": str(record.id), "status": record.status}

    async def list_pending(self, tenant_id: UUID, limit: int = 20) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(CFORecommendationRecord)
            .where(
                CFORecommendationRecord.tenant_id == tenant_id,
                CFORecommendationRecord.status == RecommendationStatus.PENDING_APPROVAL.value,
            )
            .order_by(CFORecommendationRecord.created_at.desc())
            .limit(limit)
        )
        return [self._to_dict(r) for r in result.scalars().all()]

    async def _get(self, tenant_id: UUID, recommendation_id: UUID) -> CFORecommendationRecord | None:
        result = await self.db.execute(
            select(CFORecommendationRecord).where(
                CFORecommendationRecord.id == recommendation_id,
                CFORecommendationRecord.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    def _to_dict(self, record: CFORecommendationRecord) -> dict[str, Any]:
        return {
            "id": str(record.id),
            "capability": record.capability,
            "title": record.title,
            "description": record.description,
            "rationale": record.rationale,
            "priority": record.priority,
            "confidence": record.confidence,
            "suggested_action": record.suggested_action,
            "status": record.status,
            "requires_approval": record.requires_approval,
            "created_at": record.created_at.isoformat(),
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        }
