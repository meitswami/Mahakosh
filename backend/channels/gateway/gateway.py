from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.channels.approval_actions import ChannelApprovalActions
from backend.channels.base.registry import channel_registry
from backend.channels.base.types import (
    ChannelResponse,
    ChannelType,
    IncomingMessage,
    OutgoingMessage,
)
from backend.channels.file_processor import ChannelFileProcessor
from backend.channels.routing.rate_limiter import ChannelRateLimiter
from backend.channels.routing.router import ChannelRouter
from backend.channels.session_sync import SessionSync
from backend.chat.chat_gateway import ChatGateway
from backend.models.audit import AuditLog
from backend.models.channels import ChannelAttachment as ChannelAttachmentModel
from backend.models.channels import ChannelMessage

logger = structlog.get_logger(__name__)


class CommunicationGateway:
    """
    Single entry point for all omnichannel communication.
    User → Gateway → Adapter → Chat Orchestrator → Agent Swarm → Knowledge → Response
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.router = ChannelRouter(db)
        self.rate_limiter = ChannelRateLimiter()
        self.session_sync = SessionSync(db)
        self.file_processor = ChannelFileProcessor(db)
        self.chat_gateway = ChatGateway(db)
        self.approval_actions = ChannelApprovalActions(db)

    async def receive(self, message: IncomingMessage) -> ChannelResponse:
        routing = await self.router.route(message)

        allowed, rate_info = await self.rate_limiter.check_message(
            routing.tenant_id, routing.user_id, message.channel
        )
        if not allowed:
            return ChannelResponse(text=f"Rate limit exceeded. {rate_info}")

        if message.callback_data:
            return await self._handle_approval_callback(message, routing)

        channel_session = await self.session_sync.get_or_create_channel_session(
            routing.tenant_id,
            routing.user_id,
            message.channel,
            message.external_chat_id,
            await self.session_sync.find_shared_session(routing.tenant_id, routing.user_id),
        )

        attachment_results = []
        if message.attachments:
            upload_ok, _ = await self.rate_limiter.check_upload(routing.tenant_id, routing.user_id)
            if not upload_ok:
                return ChannelResponse(text="Upload rate limit exceeded. Try again later.")
            attachment_results = await self._process_attachments(
                message, routing.tenant_id, routing.user_id
            )

        await self._persist_message(
            routing.tenant_id,
            routing.user_id,
            channel_session.id,
            message,
            direction="inbound",
        )

        chat_type = routing.assistant_mode.value if routing.assistant_mode.value != "general" else None
        pipeline = await self.chat_gateway.query(
            message=message.text,
            tenant_id=routing.tenant_id,
            user_id=routing.user_id,
            session_id=channel_session.chat_session_id,
            chat_type=chat_type,
        )

        response_text = pipeline.answer
        if attachment_results:
            wf_notes = [r.get("workflow", {}) for r in attachment_results if r.get("workflow")]
            if wf_notes:
                response_text += f"\n\n📎 {len(attachment_results)} file(s) received. OCR workflow started."

        await self._persist_message(
            routing.tenant_id,
            routing.user_id,
            channel_session.id,
            message,
            direction="outbound",
            response_text=response_text,
            pipeline=pipeline,
        )

        channel_session.last_message_at = datetime.now(UTC)
        channel_session.message_count += 2

        self.db.add(AuditLog(
            tenant_id=routing.tenant_id,
            user_id=routing.user_id,
            action="channel_message",
            entity_type="channel_session",
            entity_id=channel_session.id,
            metadata_={"channel": message.channel.value, "intent": routing.intent},
        ))

        return ChannelResponse(
            text=response_text,
            session_id=str(channel_session.id),
            chat_session_id=str(channel_session.chat_session_id),
            transparency=pipeline.transparency,
            citations=pipeline.citations,
            structured_data=pipeline.structured_data,
            agents_used=pipeline.agents_used,
            processing_time_ms=pipeline.processing_time_ms,
        )

    async def send(
        self,
        channel_type: ChannelType,
        external_chat_id: str,
        text: str,
        *,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> dict:
        adapter = channel_registry.get(channel_type)
        outgoing = OutgoingMessage(
            channel=channel_type,
            external_chat_id=external_chat_id,
            text=text,
            metadata=metadata or {},
        )
        return await adapter.send(outgoing)

    async def _handle_approval_callback(
        self,
        message: IncomingMessage,
        routing,
    ) -> ChannelResponse:
        parsed = self.approval_actions.parse_callback(message.callback_data or "")
        if not parsed:
            return ChannelResponse(text="Unknown action.")
        action, approval_id = parsed
        result = await self.approval_actions.handle_callback(
            action, approval_id, routing.tenant_id, routing.user_id, message.channel
        )
        text = f"{'✅' if result['success'] else '❌'} {result.get('title', result.get('error', 'Done'))}"
        if message.channel == ChannelType.TELEGRAM and message.metadata.get("callback_query_id"):
            adapter = channel_registry.get(ChannelType.TELEGRAM)
            if hasattr(adapter, "_token") and adapter._token:
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{adapter._token}/answerCallbackQuery",
                        json={"callback_query_id": message.metadata["callback_query_id"]},
                    )
        return ChannelResponse(text=text)

    async def _process_attachments(
        self,
        message: IncomingMessage,
        tenant_id: UUID,
        user_id: UUID,
    ) -> list[dict]:
        results = []
        for att in message.attachments:
            file_bytes = b""
            if att.file_id and message.channel == ChannelType.TELEGRAM:
                adapter = channel_registry.get(ChannelType.TELEGRAM)
                downloaded = await adapter.download_file(att.file_id)
                if downloaded:
                    file_bytes = downloaded
            if file_bytes:
                result = await self.file_processor.process(att, file_bytes, tenant_id, user_id)
                results.append(result)
        return results

    async def _persist_message(
        self,
        tenant_id: UUID,
        user_id: UUID,
        session_id: UUID,
        message: IncomingMessage,
        direction: str,
        response_text: str | None = None,
        pipeline=None,
    ) -> None:
        record = ChannelMessage(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            channel_type=message.channel.value,
            direction=direction,
            content=message.text if direction == "inbound" else (response_text or ""),
            external_message_id=message.message_id,
            intent=pipeline.intent.value if pipeline and direction == "outbound" else None,
            agents_used=pipeline.agents_used if pipeline and direction == "outbound" else [],
            transparency=pipeline.transparency if pipeline and direction == "outbound" else {},
            processing_time_ms=pipeline.processing_time_ms if pipeline and direction == "outbound" else None,
        )
        self.db.add(record)
        await self.db.flush()

        if direction == "inbound" and message.attachments:
            for att in message.attachments:
                self.db.add(ChannelAttachmentModel(
                    tenant_id=tenant_id,
                    message_id=record.id,
                    filename=att.filename,
                    content_type=att.content_type,
                    attachment_type=att.attachment_type.value,
                    size_bytes=att.size_bytes,
                    storage_path=att.storage_path,
                ))
