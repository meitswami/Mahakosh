"""Approval queue access — human-in-the-loop for sensitive operations."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.approval import ApprovalQueue


APPROVAL_REQUIRED_ACTIONS = frozenset({
    "voucher_create",
    "ledger_create",
    "item_create",
    "tally_write",
    "mass_update",
})


class ApprovalTool:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def requires_approval(action: str) -> bool:
        return action in APPROVAL_REQUIRED_ACTIONS

    async def create_request(
        self,
        tenant_id: UUID,
        user_id: UUID,
        entity_type: str,
        entity_id: UUID,
        action: str,
        title: str,
        description: str | None,
        data: dict[str, Any],
        priority: str = "normal",
        expires_hours: int = 72,
    ) -> dict[str, Any]:
        approval = ApprovalQueue(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            status="pending",
            priority=priority,
            title=title,
            description=description,
            data=data,
            requested_by=user_id,
            expires_at=datetime.now(UTC) + timedelta(hours=expires_hours),
        )
        self.db.add(approval)
        await self.db.flush()
        return {
            "approval_id": str(approval.id),
            "status": approval.status,
            "action": approval.action,
            "entity_type": approval.entity_type,
            "title": approval.title,
        }

    async def list_pending(self, tenant_id: UUID, limit: int = 50) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(ApprovalQueue)
            .where(ApprovalQueue.tenant_id == tenant_id, ApprovalQueue.status == "pending")
            .order_by(ApprovalQueue.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": str(a.id),
                "entity_type": a.entity_type,
                "entity_id": str(a.entity_id),
                "action": a.action,
                "title": a.title,
                "description": a.description,
                "priority": a.priority,
                "data": a.data,
                "requested_by": str(a.requested_by),
                "created_at": a.created_at.isoformat(),
            }
            for a in result.scalars().all()
        ]

    async def get_status(self, tenant_id: UUID, approval_id: UUID) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(ApprovalQueue).where(
                ApprovalQueue.id == approval_id,
                ApprovalQueue.tenant_id == tenant_id,
            )
        )
        approval = result.scalar_one_or_none()
        if not approval:
            return None
        return {
            "id": str(approval.id),
            "status": approval.status,
            "action": approval.action,
            "reviewed_by": str(approval.reviewed_by) if approval.reviewed_by else None,
            "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
            "review_notes": approval.review_notes,
        }
