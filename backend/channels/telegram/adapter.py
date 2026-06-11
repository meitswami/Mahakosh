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


class TelegramAdapter(BaseChannelAdapter):
    channel_type = ChannelType.TELEGRAM

    def __init__(self) -> None:
        self._token = settings.TELEGRAM_BOT_TOKEN
        self._base_url = f"https://api.telegram.org/bot{self._token}" if self._token else ""

    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            chat=True,
            document_upload=True,
            image_upload=True,
            pdf_upload=True,
            voice_upload=True,
            workflow_notifications=True,
            approval_actions=True,
            report_delivery=True,
        )

    async def send(self, message: OutgoingMessage) -> dict[str, Any]:
        if not self._token:
            logger.warning("telegram_not_configured")
            return {"status": "simulated", "text": message.text}

        payload: dict[str, Any] = {
            "chat_id": message.external_chat_id,
            "text": message.text[:4096],
        }
        if message.parse_mode:
            payload["parse_mode"] = message.parse_mode
        if message.reply_markup:
            payload["reply_markup"] = message.reply_markup

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self._base_url}/sendMessage", json=payload)
            data = resp.json()
            if not data.get("ok"):
                logger.error("telegram_send_failed", error=data)
            return data

    async def parse_webhook(self, payload: dict[str, Any]) -> IncomingMessage | None:
        if "callback_query" in payload:
            cb = payload["callback_query"]
            msg = cb.get("message", {})
            return IncomingMessage(
                channel=ChannelType.TELEGRAM,
                external_user_id=str(cb["from"]["id"]),
                external_chat_id=str(msg.get("chat", {}).get("id", cb["from"]["id"])),
                text=cb.get("data", ""),
                callback_data=cb.get("data"),
                metadata={"callback_query_id": cb.get("id"), "username": cb["from"].get("username")},
            )

        if "message" not in payload:
            return None

        msg = payload["message"]
        chat = msg.get("chat", {})
        user = msg.get("from", {})
        text = msg.get("text", "")
        attachments: list[ChannelAttachment] = []

        if "document" in msg:
            doc = msg["document"]
            fname = doc.get("file_name", "document")
            attachments.append(ChannelAttachment(
                filename=fname,
                content_type=doc.get("mime_type", "application/octet-stream"),
                attachment_type=AttachmentType.PDF if fname.lower().endswith(".pdf") else AttachmentType.OTHER,
                size_bytes=doc.get("file_size", 0),
                file_id=doc.get("file_id"),
            ))
            text = text or f"[Document: {fname}]"

        if "photo" in msg:
            photo = msg["photo"][-1]
            attachments.append(ChannelAttachment(
                filename="photo.jpg",
                content_type="image/jpeg",
                attachment_type=AttachmentType.IMAGE,
                size_bytes=photo.get("file_size", 0),
                file_id=photo.get("file_id"),
            ))
            text = text or "[Image uploaded]"

        if "voice" in msg:
            voice = msg["voice"]
            attachments.append(ChannelAttachment(
                filename="voice.ogg",
                content_type="audio/ogg",
                attachment_type=AttachmentType.AUDIO,
                size_bytes=voice.get("file_size", 0),
                file_id=voice.get("file_id"),
            ))
            text = text or "[Voice note — transcription pending]"

        return IncomingMessage(
            channel=ChannelType.TELEGRAM,
            external_user_id=str(user.get("id", "")),
            external_chat_id=str(chat.get("id", "")),
            text=text,
            attachments=attachments,
            metadata={"message_id": msg.get("message_id"), "username": user.get("username")},
        )

    async def download_file(self, file_id: str) -> bytes | None:
        if not self._token:
            return None
        async with httpx.AsyncClient(timeout=60) as client:
            meta = await client.get(f"{self._base_url}/getFile", params={"file_id": file_id})
            file_path = meta.json().get("result", {}).get("file_path")
            if not file_path:
                return None
            file_resp = await client.get(f"https://api.telegram.org/file/bot{self._token}/{file_path}")
            return file_resp.content

    async def setup_webhook(self, webhook_url: str) -> dict[str, Any]:
        if not self._token:
            return {"status": "not_configured"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base_url}/setWebhook",
                json={"url": webhook_url, "allowed_updates": ["message", "callback_query"]},
            )
            return resp.json()

    async def health_check(self) -> dict[str, Any]:
        if not self._token:
            return {"channel": "telegram", "healthy": False, "reason": "TELEGRAM_BOT_TOKEN not set"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self._base_url}/getMe")
            data = resp.json()
            return {
                "channel": "telegram",
                "healthy": data.get("ok", False),
                "bot": data.get("result", {}).get("username"),
            }
