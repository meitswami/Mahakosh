from typing import Any

import httpx
import structlog

from backend.channels.base.adapter import BaseChannelAdapter
from backend.channels.base.types import (
    AttachmentType,
    ChannelAttachment,
    ChannelCapabilities,
    ChannelType,
    IncomingMessage,
    OutgoingMessage,
)
from backend.core.config import settings

logger = structlog.get_logger(__name__)


class WhatsAppAdapter(BaseChannelAdapter):
    """Meta WhatsApp Cloud API adapter."""

    channel_type = ChannelType.WHATSAPP

    def __init__(self) -> None:
        self._token = settings.WHATSAPP_ACCESS_TOKEN
        self._phone_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self._base_url = "https://graph.facebook.com/v21.0"

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
        if not self._token or not self._phone_id:
            logger.warning("whatsapp_not_configured")
            return {"status": "simulated", "text": message.text}

        payload = {
            "messaging_product": "whatsapp",
            "to": message.external_chat_id,
            "type": "text",
            "text": {"body": message.text[:4096]},
        }
        headers = {"Authorization": f"Bearer {self._token}"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base_url}/{self._phone_id}/messages",
                json=payload,
                headers=headers,
            )
            return resp.json()

    async def parse_webhook(self, payload: dict[str, Any]) -> IncomingMessage | None:
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])
            if not messages:
                return None
            msg = messages[0]
            sender = msg.get("from", "")
            msg_type = msg.get("type", "text")
            text = ""
            attachments: list[ChannelAttachment] = []

            if msg_type == "text":
                text = msg.get("text", {}).get("body", "")
            elif msg_type == "image":
                img = msg.get("image", {})
                attachments.append(ChannelAttachment(
                    filename="image.jpg",
                    content_type="image/jpeg",
                    attachment_type=AttachmentType.IMAGE,
                    size_bytes=0,
                    file_id=img.get("id"),
                ))
                text = "[Image uploaded]"
            elif msg_type == "document":
                doc = msg.get("document", {})
                fname = doc.get("filename", "document")
                attachments.append(ChannelAttachment(
                    filename=fname,
                    content_type=doc.get("mime_type", "application/octet-stream"),
                    attachment_type=AttachmentType.PDF if fname.lower().endswith(".pdf") else AttachmentType.OTHER,
                    size_bytes=doc.get("file_size", 0),
                    file_id=doc.get("id"),
                ))
                text = f"[Document: {fname}]"
            elif msg_type == "button":
                text = msg.get("button", {}).get("payload", "")
            else:
                text = f"[{msg_type} message]"

            return IncomingMessage(
                channel=ChannelType.WHATSAPP,
                external_user_id=sender,
                external_chat_id=sender,
                text=text,
                attachments=attachments,
                metadata={"whatsapp_message_id": msg.get("id"), "type": msg_type},
            )
        except (IndexError, KeyError) as exc:
            logger.warning("whatsapp_parse_failed", error=str(exc))
            return None

    async def verify_webhook(self, payload: dict[str, Any], headers: dict[str, str]) -> bool:
        verify_token = settings.WHATSAPP_VERIFY_TOKEN
        if not verify_token:
            return True
        return payload.get("hub.verify_token") == verify_token or headers.get("x-hub-signature-256") is not None

    async def health_check(self) -> dict[str, Any]:
        configured = bool(self._token and self._phone_id)
        return {
            "channel": "whatsapp",
            "healthy": configured,
            "reason": None if configured else "WHATSAPP_ACCESS_TOKEN or PHONE_NUMBER_ID not set",
        }
