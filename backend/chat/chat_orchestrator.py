import time
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.chat.citation_engine import ChatCitationEngine
from backend.chat.context_builder import ContextBuilder
from backend.chat.conversation_manager import ConversationManager
from backend.chat.intent_engine import IntentEngine
from backend.chat.memory_manager import MemoryManager
from backend.chat.reasoning_engine import ReasoningEngine
from backend.chat.response_generator import ResponseGenerator
from backend.chat.retrieval_service import ChatRetrievalService
from backend.chat.types import (
    ChatIntent,
    ChatPipelineResult,
    ChatType,
    ReasoningStep,
    ReasoningStepType,
)
from backend.chat.transparency_builder import transparency_builder
from backend.services.agent_execution_service import AgentExecutionService

logger = structlog.get_logger(__name__)


class ChatOrchestrator:
    """Full RAG pipeline: intent → retrieval → agents → reasoning → response."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.intent_engine = IntentEngine()
        self.retrieval = ChatRetrievalService(db)
        self.context_builder = ContextBuilder(db)
        self.reasoning = ReasoningEngine()
        self.conversation = ConversationManager(db)
        self.memory = MemoryManager(db)
        self.response_gen = ResponseGenerator()
        self.citations = ChatCitationEngine()
        self.agent_service = AgentExecutionService(db)

    async def process_query(
        self,
        query: str,
        tenant_id: UUID,
        user_id: UUID,
        session_id: UUID | None = None,
        chat_type_override: str | None = None,
    ) -> ChatPipelineResult:
        start = time.perf_counter()
        steps: list[ReasoningStep] = []

        session = await self.conversation.get_or_create_session(
            tenant_id, user_id, session_id, chat_type_override or "general"
        )
        history_msgs = await self.conversation.get_messages(session.id, tenant_id)
        history = [{"role": m.role, "content": m.content, "chat_type": m.chat_type} for m in history_msgs]

        await self.conversation.add_message(session, "user", query)

        intent = self.intent_engine.detect(query, history)
        if chat_type_override:
            try:
                intent.chat_type = ChatType(chat_type_override)
            except ValueError:
                pass

        steps.append(ReasoningStep(
            ReasoningStepType.INTENT_DETECTION,
            "Intent Detection",
            f"{intent.intent.value} → {intent.chat_type.value} ({intent.confidence}%)",
            metadata=intent.to_dict(),
        ))

        filters = {**intent.filters, **{k: v for k, v in intent.entities.items() if k in ("vendor_name", "gstin", "invoice_number")}}
        collection = "invoices" if intent.chat_type == ChatType.ACCOUNTING else None

        retrieval = await self.retrieval.retrieve(
            tenant_id=tenant_id,
            query=query,
            top_k=10,
            filters=filters or None,
            collection_slug=collection,
            user_id=user_id,
        )
        chunk_previews = []
        for i, r in enumerate(retrieval.get("results", [])[:10]):
            chunk_previews.append({
                "chunk_id": str(r.chunk_id) if hasattr(r, "chunk_id") else str(r.get("chunk_id", "")),
                "document_id": str(r.document_id) if hasattr(r, "document_id") else str(r.get("document_id", "")),
                "document_title": r.document_title if hasattr(r, "document_title") else r.get("document_title", ""),
                "page_number": r.page_number if hasattr(r, "page_number") else r.get("page_number"),
                "rank": i + 1,
            })
        steps.append(ReasoningStep(
            ReasoningStepType.KNOWLEDGE_RETRIEVAL,
            "Knowledge Retrieval",
            f"Retrieved {retrieval['total_found']} chunks from knowledge base",
            metadata={
                "query_id": str(retrieval["query_id"]) if retrieval.get("query_id") else None,
                "chunks_retrieved": chunk_previews,
                "documents_consulted": [
                    {"document_id": did, "title": title}
                    for did, title in {
                        c["document_id"]: c["document_title"]
                        for c in chunk_previews if c.get("document_id")
                    }.items()
                ],
            },
        ))

        raw_citations = retrieval.get("citations", [])
        if retrieval.get("results") and not raw_citations:
            raw_citations = self.citations.from_retrieval_results(retrieval["results"])
        else:
            raw_citations = self.citations.from_dicts(raw_citations)

        knowledge_ctx = await self.retrieval.get_context(tenant_id, query, top_k=8, filters=filters or None)
        agent_outputs: dict[str, Any] = {}
        agents_used: list[str] = []

        if intent.chat_type in (ChatType.AGENT, ChatType.WORKFLOW) or intent.intent == ChatIntent.ACTION:
            agent_name = intent.agents[0] if intent.agents else "search"
            agent_result, _ = await self.agent_service.run_agent(
                agent_name, {"query": query, **intent.entities}, tenant_id, user_id
            )
            agent_outputs[agent_name] = agent_result.to_output_dict()
            agents_used.append(agent_name)
            steps.append(ReasoningStep(
                ReasoningStepType.AGENT_EXECUTION,
                f"{agent_name.replace('_', ' ').title()} Agent",
                agent_result.reasoning or f"Agent completed with {agent_result.confidence}% confidence",
                metadata={"success": agent_result.success},
            ))

        if intent.chat_type == ChatType.REPORTING:
            report_result, _ = await self.agent_service.run_agent(
                "reporting", {"query": query, "report_type": "summary"}, tenant_id, user_id
            )
            agent_outputs["reporting"] = report_result.to_output_dict()
            agents_used.append("reporting")
            steps.append(ReasoningStep(
                ReasoningStepType.AGENT_EXECUTION,
                "Reporting Agent",
                "Generated report context",
            ))

        ctx = await self.context_builder.build(
            tenant_id, user_id, query, intent,
            knowledge_ctx.get("context", ""),
            raw_citations, history, agent_outputs,
        )
        steps.append(ReasoningStep(
            ReasoningStepType.CONTEXT_BUILDING,
            "Context Building",
            f"Assembled {ctx['token_estimate']} token context",
        ))

        answer, model = await self.reasoning.reason(query, ctx["full_context"], intent, history)
        steps.append(ReasoningStep(
            ReasoningStepType.REASONING,
            "Reasoning",
            f"Generated answer using {model}",
            metadata={"model": model},
        ))

        if not answer:
            answer = self.response_gen.fallback_answer(knowledge_ctx.get("context", ""), query)

        structured = await self.reasoning.extract_structured_data(query, intent, retrieval)
        if agent_outputs:
            structured["agent_outputs"] = agent_outputs

        elapsed = int((time.perf_counter() - start) * 1000)
        pipeline = ChatPipelineResult(
            answer=answer,
            session_id=str(session.id),
            message_id=None,
            chat_type=intent.chat_type,
            intent=intent.intent,
            confidence=intent.confidence,
            citations=raw_citations,
            agents_used=agents_used or intent.agents,
            reasoning_steps=steps,
            query_id=retrieval.get("query_id"),
            processing_time_ms=elapsed,
            model_used=model,
        )

        pipeline = self.response_gen.generate(answer, pipeline, intent, structured, raw_citations)
        steps.append(ReasoningStep(
            ReasoningStepType.RESPONSE_GENERATION,
            "Response",
            f"Confidence: {pipeline.confidence}%",
        ))
        pipeline.reasoning_steps = steps

        if "search" not in pipeline.agents_used:
            pipeline.agents_used = ["search", *pipeline.agents_used]

        pipeline.transparency = transparency_builder.build(
            pipeline,
            retrieval=retrieval,
            agent_details=agent_outputs,
        )
        pipeline.structured_data["transparency"] = pipeline.transparency

        assistant_msg = await self.conversation.add_message(
            session,
            "assistant",
            pipeline.answer,
            chat_type=intent.chat_type.value,
            intent=intent.intent.value,
            confidence=pipeline.confidence,
            citations=pipeline.citations,
            structured_data=pipeline.structured_data,
            agents_used=pipeline.agents_used,
            reasoning_steps=[s.to_dict() for s in pipeline.reasoning_steps],
            model_used=model,
            processing_time_ms=elapsed,
            knowledge_query_id=retrieval.get("query_id"),
        )
        pipeline.message_id = assistant_msg.id

        await self.conversation.save_context(
            session.id, tenant_id, "pipeline", ctx["metadata"], assistant_msg.id
        )
        await self.memory.record_recent_query(
            tenant_id, user_id, query, intent.chat_type.value, intent.intent.value
        )
        await self.memory.save_session_memory(
            tenant_id, user_id, session.id, "last_intent", intent.to_dict()
        )

        return pipeline
