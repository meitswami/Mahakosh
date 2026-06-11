"""Mobile app push notification adapter foundation."""

from typing import Any

from backend.channels.base.adapter import BaseChannelAdapter
from backend.channels.base.types import (
    ChannelCapabilities,
    ChannelType,
    IncomingMessage,
    OutgoingMessage,
)


class MobileAdapter(BaseChannelAdapter):
    """Future mobile app channel — FCM/APNs integration point."""

    channel_type = ChannelType.MOBILE

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
        device_token = message.metadata.get("device_token")
        return {
            "status": "mobile_ready",
            "device_token": device_token,
            "text": message.text,
            "push_payload": {
                "title": message.metadata.get("title", "Mahakosh"),
                "body": message.text[:200],
                "data": message.metadata,
            },
        }

    async def parse_webhook(self, payload: dict[str, Any]) -> IncomingMessage | None:
        text = payload.get("message", payload.get("text", ""))
        if not text:
            return None
        return IncomingMessage(
            channel=ChannelType.MOBILE,
            external_user_id=str(payload.get("device_id", payload.get("user_id", ""))),
            external_chat_id=str(payload.get("session_id", "")),
            text=text,
            user_id=payload.get("user_id"),
            tenant_id=payload.get("tenant_id"),
            metadata={"platform": payload.get("platform", "unknown"), "app_version": payload.get("app_version")},
        )
