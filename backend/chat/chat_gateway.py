from collections.abc import AsyncGenerator
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.chat.chat_orchestrator import ChatOrchestrator
from backend.chat.conversation_manager import ConversationManager
from backend.chat.memory_manager import MemoryManager
from backend.chat.types import ChatPipelineResult
from backend.services.llm_service import llm_service

logger = structlog.get_logger(__name__)


class ChatGateway:
    """Primary entry point for all chat interactions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.orchestrator = ChatOrchestrator(db)
        self.conversation = ConversationManager(db)
        self.memory = MemoryManager(db)

    async def query(
        self,
        message: str,
        tenant_id: UUID,
        user_id: UUID,
        session_id: UUID | None = None,
        chat_type: str | None = None,
    ) -> ChatPipelineResult:
        return await self.orchestrator.process_query(
            query=message,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            chat_type_override=chat_type,
        )

    async def stream_query(
        self,
        message: str,
        tenant_id: UUID,
        user_id: UUID,
        session_id: UUID | None = None,
        chat_type: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        yield {"type": "status", "content": "Analyzing intent..."}

        pipeline = await self.orchestrator.process_query(
            query=message,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            chat_type_override=chat_type,
        )

        for step in pipeline.reasoning_steps:
            yield {"type": "reasoning_step", "content": step.to_dict()}

        yield {"type": "citations", "content": pipeline.citations}
        yield {"type": "structured_data", "content": pipeline.structured_data}
        yield {"type": "agents", "content": pipeline.agents_used}
        yield {"type": "transparency", "content": pipeline.transparency}

        words = pipeline.answer.split()
        buffer = ""
        for i, word in enumerate(words):
            buffer += word + " "
            if i % 3 == 2 or i == len(words) - 1:
                yield {"type": "token", "content": buffer}
                buffer = ""

        yield {
            "type": "done",
            "content": {
                "answer": pipeline.answer,
                "session_id": pipeline.session_id,
                "message_id": str(pipeline.message_id) if pipeline.message_id else None,
                "confidence": pipeline.transparency.get("confidence_score", pipeline.confidence),
                "processing_time_ms": pipeline.processing_time_ms,
                "chat_type": pipeline.chat_type.value,
                "intent": pipeline.intent.value,
                "citations": pipeline.citations,
                "agents_used": pipeline.agents_used,
                "reasoning_steps": [s.to_dict() for s in pipeline.reasoning_steps],
                "transparency": pipeline.transparency,
                "structured_data": pipeline.structured_data,
            },
        }

    async def get_history(self, tenant_id: UUID, user_id: UUID, limit: int = 50) -> list[dict]:
        sessions = await self.conversation.list_sessions(tenant_id, user_id, limit)
        return [
            {
                "id": str(s.id),
                "title": s.title,
                "chat_type": s.chat_type,
                "message_count": s.message_count,
                "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ]

    async def get_session(self, session_id: UUID, tenant_id: UUID, user_id: UUID) -> dict | None:
        session = await self.conversation.get_session(session_id, tenant_id, user_id)
        if not session:
            return None
        messages = await self.conversation.get_messages(session_id, tenant_id)
        return {
            "id": str(session.id),
            "title": session.title,
            "chat_type": session.chat_type,
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "chat_type": m.chat_type,
                    "intent": m.intent,
                    "confidence": m.confidence,
                    "citations": m.citations,
                    "structured_data": m.structured_data,
                    "agents_used": m.agents_used,
                    "reasoning_steps": m.reasoning_steps,
                    "transparency": m.structured_data.get("transparency") if m.structured_data else None,
                    "created_at": m.created_at.isoformat(),
                }
                for m in messages
            ],
        }

    async def delete_session(self, session_id: UUID, tenant_id: UUID, user_id: UUID) -> bool:
        return await self.conversation.delete_session(session_id, tenant_id, user_id)
