from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class ChannelType(StrEnum):
    WEBCHAT = "webchat"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    VOICE = "voice"
    MOBILE = "mobile"


class AssistantMode(StrEnum):
    ACCOUNTING = "accounting"
    DOCUMENT = "document"
    WORKFLOW = "workflow"
    REPORTING = "reporting"
    KNOWLEDGE = "knowledge"
    GENERAL = "general"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class AttachmentType(StrEnum):
    PDF = "pdf"
    IMAGE = "image"
    EXCEL = "excel"
    CSV = "csv"
    ZIP = "zip"
    WORD = "word"
    AUDIO = "audio"
    OTHER = "other"


class NotificationEvent(StrEnum):
    OCR_COMPLETED = "ocr_completed"
    APPROVAL_REQUIRED = "approval_required"
    WORKFLOW_FAILED = "workflow_failed"
    REPORT_READY = "report_ready"
    SYNC_COMPLETE = "sync_complete"
    WORKFLOW_COMPLETED = "workflow_completed"


@dataclass
class ChannelAttachment:
    filename: str
    content_type: str
    attachment_type: AttachmentType
    size_bytes: int
    storage_path: str | None = None
    file_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IncomingMessage:
    channel: ChannelType
    external_user_id: str
    external_chat_id: str
    text: str
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    session_id: UUID | None = None
    attachments: list[ChannelAttachment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    callback_data: str | None = None


@dataclass
class OutgoingMessage:
    channel: ChannelType
    external_chat_id: str
    text: str
    attachments: list[ChannelAttachment] = field(default_factory=list)
    reply_markup: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    parse_mode: str | None = None


@dataclass
class ChannelCapabilities:
    chat: bool = True
    document_upload: bool = False
    image_upload: bool = False
    pdf_upload: bool = False
    voice_upload: bool = False
    workflow_notifications: bool = False
    approval_actions: bool = False
    report_delivery: bool = False
    inbox_monitoring: bool = False


@dataclass
class RoutingContext:
    tenant_id: UUID
    user_id: UUID
    channel: ChannelType
    assistant_mode: AssistantMode
    intent: str | None = None
    permissions: list[str] = field(default_factory=list)
    session_id: UUID | None = None
    chat_session_id: UUID | None = None


@dataclass
class ChannelResponse:
    text: str
    session_id: str | None = None
    chat_session_id: str | None = None
    transparency: dict[str, Any] | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)
    structured_data: dict[str, Any] = field(default_factory=dict)
    agents_used: list[str] = field(default_factory=list)
    processing_time_ms: int = 0
