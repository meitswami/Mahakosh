from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class WorkflowEventType(StrEnum):
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    WORKFLOW_RETRIED = "workflow_retried"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_WAITING = "step_waiting"
    STEP_RETRIED = "step_retried"
    AGENT_INVOKED = "agent_invoked"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"
    VALIDATION_FAILED = "validation_failed"


class NodeType(StrEnum):
    START = "start"
    TASK = "task"
    AGENT = "agent"
    VALIDATION = "validation"
    APPROVAL = "approval"
    DECISION = "decision"
    END = "end"


class WorkflowType(StrEnum):
    DOCUMENT = "document_processing"
    OCR = "ocr_processing"
    KNOWLEDGE = "knowledge_indexing"
    ACCOUNTING = "accounting_workflow"
    APPROVAL = "approval_flow"
    REPORTING = "report_generation"
    AGENT = "agent_workflow"
    GST = "gst_validation"
    VENDOR_ONBOARDING = "vendor_onboarding"
    ITEM_CREATION = "item_creation"
    TALLY_EXPORT = "tally_export"
    CUSTOM = "custom"


@dataclass
class WorkflowEvent:
    event_type: WorkflowEventType
    workflow_id: UUID
    tenant_id: UUID
    payload: dict[str, Any] = field(default_factory=dict)
    step_name: str | None = None
    agent_name: str | None = None
    user_id: UUID | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["workflow_id"] = str(self.workflow_id)
        data["tenant_id"] = str(self.tenant_id)
        if self.user_id:
            data["user_id"] = str(self.user_id)
        return data
