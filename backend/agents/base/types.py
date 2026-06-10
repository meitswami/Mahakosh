from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class AgentStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEGRADED = "degraded"
    SHUTDOWN = "shutdown"


class ConfidenceLevel(StrEnum):
    HIGH = "high"          # 95+
    MEDIUM = "medium"      # 80-95
    NEEDS_REVIEW = "needs_review"  # below 80


class ExecutionMode(StrEnum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BATCH = "batch"


class AgentEventType(StrEnum):
    DOCUMENT_RECEIVED = "document_received"
    OCR_COMPLETED = "ocr_completed"
    VALIDATION_COMPLETED = "validation_completed"
    GST_DETECTED = "gst_detected"
    ITEM_CREATED = "item_created"
    VENDOR_MATCHED = "vendor_matched"
    WORKFLOW_COMPLETED = "workflow_completed"
    APPROVAL_REQUIRED = "approval_required"
    TALLY_EXPORT_READY = "tally_export_ready"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    CONSENSUS_REACHED = "consensus_reached"


def confidence_level(score: float) -> ConfidenceLevel:
    if score >= 95:
        return ConfidenceLevel.HIGH
    if score >= 80:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.NEEDS_REVIEW


@dataclass
class AgentContext:
    tenant_id: UUID
    user_id: UUID | None = None
    workflow_id: UUID | None = None
    workflow_step_id: UUID | None = None
    parent_execution_id: UUID | None = None
    execution_id: UUID | None = None
    task_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    reasoning: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    tokens_used: int | None = None
    processing_time_ms: int | None = None
    next_agents: list[str] = field(default_factory=list)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        return confidence_level(self.confidence)

    def to_output_dict(self) -> dict[str, Any]:
        return {
            "result": self.data,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "reasoning": self.reasoning,
            "sources": self.sources,
            "execution_time": self.processing_time_ms,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class AgentHealthReport:
    agent_name: str
    status: AgentStatus
    healthy: bool
    execution_count: int = 0
    success_rate: float = 100.0
    average_runtime_ms: float = 0.0
    queue_length: int = 0
    last_error: str | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
