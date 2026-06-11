import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CommunicationChannel(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "communication_channels"

    channel_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="inactive", nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bot_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class ChannelUser(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "channel_users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    external_chat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class ChannelSession(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "channel_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_chat_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    chat_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class ChannelMessage(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "channel_messages"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channel_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    external_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    agents_used: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    transparency: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class ChannelAttachment(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "channel_attachments"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channel_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    attachment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ChannelNotification(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "channel_notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
