from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.channels.base.types import AssistantMode, ChannelType, IncomingMessage, RoutingContext
from backend.chat.intent_engine import IntentEngine
from backend.models.channels import ChannelUser
from backend.models.user import User

logger = structlog.get_logger(__name__)

MODE_MAP = {
    "accounting": AssistantMode.ACCOUNTING,
    "document": AssistantMode.DOCUMENT,
    "workflow": AssistantMode.WORKFLOW,
    "reporting": AssistantMode.REPORTING,
    "knowledge": AssistantMode.KNOWLEDGE,
    "search": AssistantMode.KNOWLEDGE,
    "general": AssistantMode.GENERAL,
}


class ChannelRouter:
    """Determine user, tenant, permissions, intent, and channel routing."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.intent_engine = IntentEngine()

    async def route(self, message: IncomingMessage) -> RoutingContext:
        tenant_id, user_id = await self._resolve_user(message)

        intent_result = self.intent_engine.detect(message.text)
        assistant_mode = MODE_MAP.get(intent_result.chat_type.value, AssistantMode.GENERAL)

        permissions = await self._get_permissions(user_id)

        return RoutingContext(
            tenant_id=tenant_id,
            user_id=user_id,
            channel=message.channel,
            assistant_mode=assistant_mode,
            intent=intent_result.intent.value,
            permissions=permissions,
            session_id=message.session_id,
        )

    async def _resolve_user(self, message: IncomingMessage) -> tuple[UUID, UUID]:
        if message.tenant_id and message.user_id:
            return message.tenant_id, message.user_id

        result = await self.db.execute(
            select(ChannelUser).where(
                ChannelUser.channel_type == message.channel.value,
                ChannelUser.external_user_id == message.external_user_id,
                ChannelUser.is_active.is_(True),
            )
        )
        channel_user = result.scalar_one_or_none()
        if channel_user:
            return channel_user.tenant_id, channel_user.user_id

        raise ValueError(
            f"Unlinked {message.channel.value} user {message.external_user_id}. "
            "Link account via /api/v1/channels/link"
        )

    async def _get_permissions(self, user_id: UUID) -> list[str]:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return []
        from backend.models.role import Role
        role_result = await self.db.execute(select(Role).where(Role.id == user.role_id))
        role = role_result.scalar_one_or_none()
        return list(role.permissions) if role else []
