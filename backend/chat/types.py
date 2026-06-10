from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID


class ChatType(StrEnum):
    GENERAL = "general"
    KNOWLEDGE = "knowledge"
    DOCUMENT = "document"
    ACCOUNTING = "accounting"
    WORKFLOW = "workflow"
    REPORTING = "reporting"
    AGENT = "agent"


class ChatIntent(StrEnum):
    SEARCH = "search"
    REPORT = "report"
    ACCOUNTING_QUERY = "accounting_query"
    WORKFLOW_QUERY = "workflow_query"
    DOCUMENT_QUERY = "document_query"
    ANALYTICAL = "analytical"
    ACTION = "action"
    GENERAL = "general"


class ReasoningStepType(StrEnum):
    INTENT_DETECTION = "intent_detection"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    AGENT_EXECUTION = "agent_execution"
    CONTEXT_BUILDING = "context_building"
    REASONING = "reasoning"
    RESPONSE_GENERATION = "response_generation"


@dataclass
class ReasoningStep:
    step_type: ReasoningStepType
    label: str
    detail: str
    status: str = "completed"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_type": self.step_type.value,
            "label": self.label,
            "detail": self.detail,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class IntentResult:
    intent: ChatIntent
    chat_type: ChatType
    confidence: float
    entities: dict[str, Any] = field(default_factory=dict)
    agents: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.value,
            "chat_type": self.chat_type.value,
            "confidence": self.confidence,
            "entities": self.entities,
            "agents": self.agents,
            "filters": self.filters,
        }


@dataclass
class ChatPipelineResult:
    answer: str
    session_id: str
    message_id: UUID | None
    chat_type: ChatType
    intent: ChatIntent
    confidence: float
    citations: list[dict[str, Any]] = field(default_factory=list)
    structured_data: dict[str, Any] = field(default_factory=dict)
    agents_used: list[str] = field(default_factory=list)
    reasoning_steps: list[ReasoningStep] = field(default_factory=list)
    transparency: dict[str, Any] = field(default_factory=dict)
    query_id: UUID | None = None
    processing_time_ms: int = 0
    model_used: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "session_id": self.session_id,
            "message_id": str(self.message_id) if self.message_id else None,
            "chat_type": self.chat_type.value,
            "intent": self.intent.value,
            "confidence": self.confidence,
            "citations": self.citations,
            "structured_data": self.structured_data,
            "agents_used": self.agents_used,
            "reasoning_steps": [s.to_dict() for s in self.reasoning_steps],
            "transparency": self.transparency,
            "query_id": str(self.query_id) if self.query_id else None,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
        }
