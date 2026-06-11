import email
import imaplib
from email.header import decode_header
from typing import Any

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

EXTENSION_MAP = {
    ".pdf": AttachmentType.PDF,
    ".png": AttachmentType.IMAGE,
    ".jpg": AttachmentType.IMAGE,
    ".jpeg": AttachmentType.IMAGE,
    ".xlsx": AttachmentType.EXCEL,
    ".xls": AttachmentType.EXCEL,
    ".csv": AttachmentType.CSV,
    ".zip": AttachmentType.ZIP,
    ".docx": AttachmentType.WORD,
    ".doc": AttachmentType.WORD,
}


class EmailAdapter(BaseChannelAdapter):
    channel_type = ChannelType.EMAIL

    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            chat=True,
            document_upload=True,
            image_upload=True,
            pdf_upload=True,
            inbox_monitoring=True,
            workflow_notifications=True,
            approval_actions=True,
            report_delivery=True,
        )

    async def send(self, message: OutgoingMessage) -> dict[str, Any]:
        import asyncio
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        if not settings.EMAIL_SMTP_HOST:
            return {"status": "simulated", "to": message.external_chat_id, "text": message.text}

        msg = MIMEMultipart()
        msg["From"] = settings.EMAIL_FROM_ADDRESS
        msg["To"] = message.external_chat_id
        msg["Subject"] = message.metadata.get("subject", "Mahakosh Notification")
        msg.attach(MIMEText(message.text, "plain"))

        def _send() -> None:
            with smtplib.SMTP(settings.EMAIL_SMTP_HOST, settings.EMAIL_SMTP_PORT) as server:
                if settings.EMAIL_SMTP_USE_TLS:
                    server.starttls()
                if settings.EMAIL_SMTP_USER:
                    server.login(settings.EMAIL_SMTP_USER, settings.EMAIL_SMTP_PASSWORD)
                server.send_message(msg)

        await asyncio.to_thread(_send)
        return {"status": "sent", "to": message.external_chat_id}

    async def parse_webhook(self, payload: dict[str, Any]) -> IncomingMessage | None:
        return self._parse_email_payload(payload)

    def _parse_email_payload(self, payload: dict[str, Any]) -> IncomingMessage | None:
        if "raw_email" in payload:
            return self._parse_raw_email(payload["raw_email"], payload.get("tenant_id"))

        sender = payload.get("from", payload.get("sender", ""))
        subject = payload.get("subject", "")
        body = payload.get("body", payload.get("text", ""))
        if not sender:
            return None

        attachments: list[ChannelAttachment] = []
        for att in payload.get("attachments", []):
            fname = att.get("filename", "attachment")
            ext = "." + fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
            attachments.append(ChannelAttachment(
                filename=fname,
                content_type=att.get("content_type", "application/octet-stream"),
                attachment_type=EXTENSION_MAP.get(ext, AttachmentType.OTHER),
                size_bytes=att.get("size", 0),
                storage_path=att.get("storage_path"),
            ))

        return IncomingMessage(
            channel=ChannelType.EMAIL,
            external_user_id=sender,
            external_chat_id=sender,
            text=f"Subject: {subject}\n\n{body}",
            attachments=attachments,
            metadata={"subject": subject, "from": sender},
        )

    def _parse_raw_email(self, raw: bytes | str, tenant_id: Any = None) -> IncomingMessage | None:
        msg = email.message_from_bytes(raw.encode() if isinstance(raw, str) else raw)
        sender = msg.get("From", "")
        subject = self._decode_header(msg.get("Subject", ""))
        body = ""
        attachments: list[ChannelAttachment] = []

        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition", ""))
                if "attachment" in disp:
                    fname = part.get_filename() or "attachment"
                    fname = self._decode_header(fname)
                    ext = "." + fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                    attachments.append(ChannelAttachment(
                        filename=fname,
                        content_type=ctype,
                        attachment_type=EXTENSION_MAP.get(ext, AttachmentType.OTHER),
                        size_bytes=len(part.get_payload(decode=True) or b""),
                    ))
                elif ctype == "text/plain" and not body:
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
        else:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

        return IncomingMessage(
            channel=ChannelType.EMAIL,
            external_user_id=sender,
            external_chat_id=sender,
            text=f"Subject: {subject}\n\n{body}",
            attachments=attachments,
            metadata={"subject": subject},
        )

    def _decode_header(self, value: str) -> str:
        parts = decode_header(value)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(part)
        return "".join(decoded)

    async def poll_inbox(self) -> list[IncomingMessage]:
        if not settings.EMAIL_IMAP_HOST:
            return []
        messages: list[IncomingMessage] = []
        try:
            mail = imaplib.IMAP4_SSL(settings.EMAIL_IMAP_HOST, settings.EMAIL_IMAP_PORT)
            mail.login(settings.EMAIL_IMAP_USER, settings.EMAIL_IMAP_PASSWORD)
            mail.select("INBOX")
            _, data = mail.search(None, "UNSEEN")
            for num in data[0].split()[:20]:
                _, msg_data = mail.fetch(num, "(RFC822)")
                raw = msg_data[0][1]
                parsed = self._parse_raw_email(raw)
                if parsed:
                    messages.append(parsed)
            mail.logout()
        except Exception as exc:
            logger.error("email_poll_failed", error=str(exc))
        return messages

    async def health_check(self) -> dict[str, Any]:
        smtp_ok = bool(settings.EMAIL_SMTP_HOST)
        imap_ok = bool(settings.EMAIL_IMAP_HOST)
        return {
            "channel": "email",
            "healthy": smtp_ok or imap_ok,
            "smtp_configured": smtp_ok,
            "imap_configured": imap_ok,
        }
