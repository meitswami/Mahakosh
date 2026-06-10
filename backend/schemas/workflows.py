from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowStepResponse(BaseModel):
    id: UUID
    step_name: str
    step_order: int
    agent_name: str | None
    node_type: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    retry_count: int = 0

    model_config = {"from_attributes": True}


class WorkflowSummaryResponse(BaseModel):
    id: UUID
    name: str
    workflow_type: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    assigned_agents: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowGraphNode(BaseModel):
    id: str
    type: str
    label: str
    status: str
    agent_name: str | None = None
    step_order: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    retry_count: int | None = None
    replay: dict[str, Any] | None = None


class WorkflowGraphEdge(BaseModel):
    from_: str = Field(alias="from")
    to: str
    type: str = "sequential"

    model_config = {"populate_by_name": True}


class WorkflowGraphResponse(BaseModel):
    workflow_id: str
    workflow_name: str
    workflow_type: str
    status: str
    nodes: list[WorkflowGraphNode]
    edges: list[WorkflowGraphEdge]
    assigned_agents: list[str] = Field(default_factory=list)


class TimelineEntry(BaseModel):
    type: str
    label: str
    status: str
    timestamp: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None
    agent_name: str | None = None
    error: str | None = None
    retry_count: int | None = None
    reasoning_summary: str | None = None
    confidence: float | None = None
    step_id: str | None = None
    payload: dict[str, Any] | None = None


class WorkflowLogResponse(BaseModel):
    id: UUID
    action: str
    agent_name: str | None
    step_id: UUID | None
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    reasoning_summary: str | None
    confidence: float | None
    duration_ms: int | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LiveWorkflowResponse(BaseModel):
    id: str
    name: str
    workflow_type: str
    status: str
    progress: int
    current_step: str | None
    current_agent: str | None
    started_at: str | None
    assigned_agents: list[str] | None = None


class AgentActivityResponse(BaseModel):
    agent_name: str
    status: str
    healthy: bool
    queue_length: int
    execution_count: int
    average_runtime_ms: float
    success_rate: float
    last_error: str | None


class WorkflowAnalyticsResponse(BaseModel):
    period_days: int
    completed_workflows: int
    failed_workflows: int
    success_rate: float
    average_duration_ms: float
    agent_utilization: dict[str, int]
    active_agents: int


class WorkflowTemplateResponse(BaseModel):
    name: str
    workflow_type: str
    description: str
    step_count: int
    agents: list[str]


class WorkflowCreateRequest(BaseModel):
    name: str
    workflow_type: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    entity_type: str | None = None
    entity_id: UUID | None = None


class WorkflowRetryRequest(BaseModel):
    workflow_id: UUID
    from_step: str | None = None


class WorkflowCancelRequest(BaseModel):
    workflow_id: UUID


class ApprovalItemResponse(BaseModel):
    id: str
    title: str
    action: str | None = None
    status: str | None = None
    entity_type: str | None = None
    priority: str | None = None
    created_at: str | None = None
    reviewed_at: str | None = None
    review_notes: str | None = None


class WorkflowAgentExecuted(BaseModel):
    name: str
    step_name: str
    step_order: int
    node_type: str | None = None
    status: str
    purpose: str
    reasoning: str
    confidence: float | None = None
    duration_ms: int | None = None
    error: str | None = None
    retry_count: int = 0


class WorkflowDocumentUsed(BaseModel):
    document_id: str
    title: str
    document_type: str | None = None
    used_in_steps: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    page_numbers: list[int] = Field(default_factory=list)


class WorkflowValidationPerformed(BaseModel):
    step_name: str
    agent_name: str | None
    status: str
    is_valid: bool
    checks_passed: list[str] = Field(default_factory=list)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: str = ""
    confidence: float | None = None


class WorkflowApprovalRecord(BaseModel):
    approval_id: str | None = None
    title: str
    status: str
    action: str | None = None
    requested_by: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    review_notes: str | None = None


class WorkflowTransparencyQuestions(BaseModel):
    what_happened: str
    why_did_it_happen: str
    which_agent_executed: str
    which_documents_were_used: str
    which_validations_were_performed: str
    who_approved_it: str


class WorkflowTransparencyResponse(BaseModel):
    workflow_id: str
    workflow_name: str
    workflow_type: str
    status: str
    what_happened: str
    why_it_happened: str
    summary: str
    confidence_score: float
    confidence_level: str
    confidence_display: str
    processing_time_ms: int | None = None
    agents_executed: list[WorkflowAgentExecuted] = Field(default_factory=list)
    documents_used: list[WorkflowDocumentUsed] = Field(default_factory=list)
    validations_performed: list[WorkflowValidationPerformed] = Field(default_factory=list)
    approvals: list[WorkflowApprovalRecord] = Field(default_factory=list)
    reasoning_path: list[dict[str, Any]] = Field(default_factory=list)
    questions: WorkflowTransparencyQuestions


class WorkflowDetailResponse(WorkflowSummaryResponse):
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    duration_ms: int | None = None
    steps: list[WorkflowStepResponse] = Field(default_factory=list)
    created_by: UUID
    transparency: WorkflowTransparencyResponse | None = None
