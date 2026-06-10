from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.approval import ApprovalQueue
from backend.models.workflow_monitoring import WorkflowApprovalLink


class ApprovalManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def link_approval(
        self,
        tenant_id: UUID,
        workflow_id: UUID,
        approval_id: UUID,
        step_id: UUID | None = None,
    ) -> WorkflowApprovalLink:
        link = WorkflowApprovalLink(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            step_id=step_id,
            approval_id=approval_id,
            status="pending",
        )
        self.db.add(link)
        await self.db.flush()
        return link

    async def get_workflow_approvals(self, tenant_id: UUID, workflow_id: UUID) -> list[dict]:
        result = await self.db.execute(
            select(WorkflowApprovalLink, ApprovalQueue)
            .join(ApprovalQueue, WorkflowApprovalLink.approval_id == ApprovalQueue.id)
            .where(
                WorkflowApprovalLink.tenant_id == tenant_id,
                WorkflowApprovalLink.workflow_id == workflow_id,
            )
        )
        return [
            {
                "link_id": str(link.id),
                "approval_id": str(approval.id),
                "status": approval.status,
                "title": approval.title,
                "action": approval.action,
                "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
                "review_notes": approval.review_notes,
            }
            for link, approval in result.all()
        ]

    async def list_pending(self, tenant_id: UUID, limit: int = 50) -> list[dict]:
        result = await self.db.execute(
            select(ApprovalQueue)
            .where(ApprovalQueue.tenant_id == tenant_id, ApprovalQueue.status == "pending")
            .order_by(ApprovalQueue.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": str(a.id),
                "title": a.title,
                "action": a.action,
                "entity_type": a.entity_type,
                "priority": a.priority,
                "created_at": a.created_at.isoformat(),
            }
            for a in result.scalars().all()
        ]

    async def list_history(self, tenant_id: UUID, limit: int = 50) -> list[dict]:
        result = await self.db.execute(
            select(ApprovalQueue)
            .where(
                ApprovalQueue.tenant_id == tenant_id,
                ApprovalQueue.status.in_(["approved", "rejected", "modified"]),
            )
            .order_by(ApprovalQueue.reviewed_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": str(a.id),
                "title": a.title,
                "status": a.status,
                "action": a.action,
                "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
                "review_notes": a.review_notes,
            }
            for a in result.scalars().all()
        ]
