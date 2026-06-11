from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChannelConnectRequest(BaseModel):
    channel_type: str
    name: str
    config: dict[str, Any] = Field(default_factory=dict)
    webhook_url: str | None = None


class ChannelLinkRequest(BaseModel):
    channel_type: str
    external_user_id: str
    external_chat_id: str
    external_username: str | None = None


class ChannelSendRequest(BaseModel):
    channel_type: str
    external_chat_id: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChannelReceiveRequest(BaseModel):
    channel_type: str
    message: str
    external_user_id: str | None = None
    external_chat_id: str | None = None
    session_id: UUID | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChannelResponse(BaseModel):
    text: str
    session_id: str | None = None
    chat_session_id: str | None = None
    transparency: dict[str, Any] | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    agents_used: list[str] = Field(default_factory=list)
    processing_time_ms: int = 0


class ChannelSummary(BaseModel):
    id: UUID
    channel_type: str
    name: str
    status: str
    bot_username: str | None = None
    is_active: bool
    last_sync_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChannelSessionResponse(BaseModel):
    id: UUID
    channel_type: str
    external_chat_id: str
    chat_session_id: UUID | None
    status: str
    message_count: int
    last_message_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChannelMessageResponse(BaseModel):
    id: UUID
    channel_type: str
    direction: str
    content: str
    intent: str | None = None
    agents_used: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class ChannelDashboardResponse(BaseModel):
    connected_channels: list[ChannelSummary]
    active_sessions: int
    total_messages: int
    active_users: int
    recent_notifications: list[dict[str, Any]] = Field(default_factory=list)
    channel_health: list[dict[str, Any]] = Field(default_factory=list)
    rate_limits: dict[str, Any] = Field(default_factory=dict)
