from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.channels.base.types import ChannelType, OutgoingMessage
from backend.models.approval import ApprovalQueue
from backend.models.audit import AuditLog

logger = structlog.get_logger(__name__)


class ChannelApprovalActions:
    """Handle approve/reject/review actions from Telegram, WhatsApp, and other channels."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def handle_callback(
        self,
        action: str,
        approval_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        channel: ChannelType,
        notes: str | None = None,
    ) -> dict:
        result = await self.db.execute(
            select(ApprovalQueue).where(
                ApprovalQueue.id == approval_id,
                ApprovalQueue.tenant_id == tenant_id,
                ApprovalQueue.status == "pending",
            )
        )
        approval = result.scalar_one_or_none()
        if not approval:
            return {"success": False, "error": "Approval not found or already resolved"}

        if action == "approve":
            approval.status = "approved"
        elif action == "reject":
            approval.status = "rejected"
        elif action == "review":
            approval.status = "modified"
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

        approval.reviewed_by = user_id
        approval.reviewed_at = datetime.now(UTC)
        approval.review_notes = notes or f"{action} via {channel.value}"

        self.db.add(AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=f"approval_{action}",
            entity_type="approval",
            entity_id=approval_id,
            metadata_={"channel": channel.value, "title": approval.title},
        ))
        await self.db.flush()

        return {
            "success": True,
            "approval_id": str(approval_id),
            "status": approval.status,
            "title": approval.title,
        }

    def parse_callback(self, callback_data: str) -> tuple[str, UUID] | None:
        if ":" not in callback_data:
            return None
        action, approval_id_str = callback_data.split(":", 1)
        if action not in ("approve", "reject", "review"):
            return None
        try:
            return action, UUID(approval_id_str)
        except ValueError:
            return None

    def build_response_message(self, result: dict) -> OutgoingMessage:
        if result.get("success"):
            text = f"✅ {result['title']} — {result['status'].upper()}"
        else:
            text = f"❌ Action failed: {result.get('error', 'Unknown error')}"
        return OutgoingMessage(
            channel=ChannelType.TELEGRAM,
            external_chat_id="",
            text=text,
        )
