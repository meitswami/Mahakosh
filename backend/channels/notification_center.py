from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.channels.base.registry import channel_registry
from backend.channels.base.types import ChannelType, NotificationEvent, OutgoingMessage
from backend.channels.templates.messages import render_notification
from backend.models.channels import ChannelNotification, ChannelUser, CommunicationChannel
from backend.models.notification import Notification

logger = structlog.get_logger(__name__)


class NotificationCenter:
    """Centralized notification system — fans out to Web, Email, Telegram, WhatsApp."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def notify(
        self,
        tenant_id: UUID,
        user_id: UUID,
        event: NotificationEvent,
        data: dict,
        *,
        channels: list[ChannelType] | None = None,
    ) -> list[dict]:
        results: list[dict] = []

        web_result = await self._notify_web(tenant_id, user_id, event, data)
        results.append(web_result)

        target_channels = channels or await self._get_user_channels(tenant_id, user_id)
        for channel_type in target_channels:
            if channel_type == ChannelType.WEBCHAT:
                continue
            result = await self._notify_channel(tenant_id, user_id, channel_type, event, data)
            results.append(result)

        return results

    async def _notify_web(
        self,
        tenant_id: UUID,
        user_id: UUID,
        event: NotificationEvent,
        data: dict,
    ) -> dict:
        rendered = render_notification(event, "web", **{k: str(v) for k, v in data.items()})
        notif = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title=rendered.get("title", "Mahakosh"),
            message=rendered.get("body", ""),
            notification_type=event.value,
            data=data,
            entity_type=data.get("entity_type"),
            entity_id=data.get("entity_id"),
        )
        self.db.add(notif)
        await self.db.flush()
        return {"channel": "web", "status": "delivered", "notification_id": str(notif.id)}

    async def _notify_channel(
        self,
        tenant_id: UUID,
        user_id: UUID,
        channel_type: ChannelType,
        event: NotificationEvent,
        data: dict,
    ) -> dict:
        channel_user = await self._get_channel_user(tenant_id, user_id, channel_type)
        if not channel_user:
            return {"channel": channel_type.value, "status": "skipped", "reason": "not_linked"}

        rendered = render_notification(event, channel_type.value, **{k: str(v) for k, v in data.items()})
        adapter = channel_registry.get(channel_type)

        outgoing = OutgoingMessage(
            channel=channel_type,
            external_chat_id=channel_user.external_chat_id,
            text=rendered.get("text", rendered.get("body", "")),
            metadata={"subject": rendered.get("email_subject", rendered.get("title"))},
        )

        if event == NotificationEvent.APPROVAL_REQUIRED and data.get("approval_id"):
            outgoing.reply_markup = adapter.format_approval_keyboard(str(data["approval_id"]))

        try:
            send_result = await adapter.send(outgoing)
            status = "delivered" if send_result.get("ok", send_result.get("status") == "sent") else "failed"
        except Exception as exc:
            logger.error("notification_send_failed", channel=channel_type.value, error=str(exc))
            status = "failed"
            send_result = {"error": str(exc)}

        record = ChannelNotification(
            tenant_id=tenant_id,
            user_id=user_id,
            channel_type=channel_type.value,
            event_type=event.value,
            title=rendered.get("title", ""),
            message=rendered.get("body", ""),
            status=status,
            payload=data,
        )
        self.db.add(record)
        await self.db.flush()

        return {"channel": channel_type.value, "status": status, "notification_id": str(record.id)}

    async def _get_user_channels(self, tenant_id: UUID, user_id: UUID) -> list[ChannelType]:
        result = await self.db.execute(
            select(ChannelUser).where(
                ChannelUser.tenant_id == tenant_id,
                ChannelUser.user_id == user_id,
                ChannelUser.is_active.is_(True),
            )
        )
        users = result.scalars().all()
        return [ChannelType(cu.channel_type) for cu in users]

    async def _get_channel_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        channel_type: ChannelType,
    ) -> ChannelUser | None:
        result = await self.db.execute(
            select(ChannelUser).where(
                ChannelUser.tenant_id == tenant_id,
                ChannelUser.user_id == user_id,
                ChannelUser.channel_type == channel_type.value,
                ChannelUser.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_dashboard(self, tenant_id: UUID) -> dict:
        channels_result = await self.db.execute(
            select(CommunicationChannel).where(
                CommunicationChannel.tenant_id == tenant_id,
                CommunicationChannel.is_active.is_(True),
            )
        )
        channels = list(channels_result.scalars().all())

        notif_result = await self.db.execute(
            select(ChannelNotification)
            .where(ChannelNotification.tenant_id == tenant_id)
            .order_by(ChannelNotification.created_at.desc())
            .limit(20)
        )
        recent = list(notif_result.scalars().all())

        return {
            "connected_channels": [
                {"type": c.channel_type, "name": c.name, "status": c.status}
                for c in channels
            ],
            "recent_notifications": [
                {
                    "id": str(n.id),
                    "channel": n.channel_type,
                    "event": n.event_type,
                    "title": n.title,
                    "status": n.status,
                    "created_at": n.created_at.isoformat(),
                }
                for n in recent
            ],
        }
