from typing import Any

from backend.channels.base.adapter import BaseChannelAdapter
from backend.channels.base.types import (
    ChannelCapabilities,
    ChannelType,
    IncomingMessage,
    OutgoingMessage,
)


class WebChatAdapter(BaseChannelAdapter):
    """Web chat adapter — delegates to the existing Mahakosh chat UI."""

    channel_type = ChannelType.WEBCHAT

    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            chat=True,
            document_upload=True,
            image_upload=True,
            pdf_upload=True,
            workflow_notifications=True,
            approval_actions=True,
            report_delivery=True,
        )

    async def send(self, message: OutgoingMessage) -> dict[str, Any]:
        return {
            "status": "delivered",
            "channel": "webchat",
            "text": message.text,
            "metadata": message.metadata,
        }

    async def parse_webhook(self, payload: dict[str, Any]) -> IncomingMessage | None:
        text = payload.get("message", payload.get("text", ""))
        if not text and not payload.get("attachments"):
            return None
        return IncomingMessage(
            channel=ChannelType.WEBCHAT,
            external_user_id=str(payload.get("user_id", "")),
            external_chat_id=str(payload.get("session_id", payload.get("user_id", ""))),
            text=text,
            user_id=payload.get("user_id"),
            tenant_id=payload.get("tenant_id"),
            session_id=payload.get("session_id"),
            metadata=payload.get("metadata", {}),
        )
