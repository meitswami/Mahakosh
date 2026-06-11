from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.channels.base.types import ChannelType
from backend.models.channels import ChannelSession
from backend.models.chat import ChatSession


class SessionSync:
    """
    Cross-channel conversation synchronization.
    Same user on Web → Telegram → WhatsApp shares one chat session memory.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_channel_session(
        self,
        tenant_id: UUID,
        user_id: UUID,
        channel: ChannelType,
        external_chat_id: str,
        chat_session_id: UUID | None = None,
    ) -> ChannelSession:
        result = await self.db.execute(
            select(ChannelSession).where(
                ChannelSession.tenant_id == tenant_id,
                ChannelSession.user_id == user_id,
                ChannelSession.channel_type == channel.value,
                ChannelSession.external_chat_id == external_chat_id,
                ChannelSession.status == "active",
            )
        )
        session = result.scalar_one_or_none()
        if session:
            return session

        if not chat_session_id:
            chat_session = ChatSession(
                tenant_id=tenant_id,
                user_id=user_id,
                chat_type="general",
                title=f"{channel.value.title()} Conversation",
                metadata_={"channels": [channel.value]},
            )
            self.db.add(chat_session)
            await self.db.flush()
            chat_session_id = chat_session.id
        else:
            chat_result = await self.db.execute(
                select(ChatSession).where(
                    ChatSession.id == chat_session_id,
                    ChatSession.tenant_id == tenant_id,
                    ChatSession.user_id == user_id,
                )
            )
            chat_session = chat_result.scalar_one_or_none()
            if chat_session:
                channels = chat_session.metadata_.get("channels", [])
                if channel.value not in channels:
                    channels.append(channel.value)
                    chat_session.metadata_["channels"] = channels

        channel_session = ChannelSession(
            tenant_id=tenant_id,
            user_id=user_id,
            channel_type=channel.value,
            external_chat_id=external_chat_id,
            chat_session_id=chat_session_id,
            status="active",
        )
        self.db.add(channel_session)
        await self.db.flush()
        return channel_session

    async def find_shared_session(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> UUID | None:
        """Find the most recent active chat session across any channel."""
        result = await self.db.execute(
            select(ChannelSession)
            .where(
                ChannelSession.tenant_id == tenant_id,
                ChannelSession.user_id == user_id,
                ChannelSession.status == "active",
            )
            .order_by(ChannelSession.last_message_at.desc().nullslast())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        return session.chat_session_id if session else None
