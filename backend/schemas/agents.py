from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentInfoResponse(BaseModel):
    name: str
    version: str
    description: str
    capabilities: list[str]
    status: str = "idle"
    execution_count: int = 0
    success_rate: float = 100.0
    average_runtime_ms: float = 0.0


class AgentExecuteRequest(BaseModel):
    input_data: dict = Field(default_factory=dict)
    model_name: str | None = None


class AgentExecuteResponse(BaseModel):
    success: bool
    agent_name: str
    execution_id: UUID | None = None
    data: dict = Field(default_factory=dict)
    confidence: float = 0.0
    confidence_level: str = "needs_review"
    reasoning: str = ""
    sources: list = Field(default_factory=list)
    error: str | None = None
    processing_time_ms: int | None = None


class AgentHealthResponse(BaseModel):
    agent_name: str
    status: str
    healthy: bool
    execution_count: int
    success_rate: float
    average_runtime_ms: float
    queue_length: int
    last_error: str | None = None


class AgentExecutionResponse(BaseModel):
    id: UUID
    agent_name: str
    status: str
    confidence: float | None
    processing_time_ms: int | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentEventResponse(BaseModel):
    id: UUID
    event_type: str
    source_agent: str
    payload: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentStatusResponse(BaseModel):
    total_agents: int
    active_tasks: int
    agents: list[AgentInfoResponse]
    health: list[AgentHealthResponse]


class OrchestratorRequest(BaseModel):
    task_type: str = "general"
    payload: dict = Field(default_factory=dict)
    execution_mode: str = "sequential"


class OrchestratorResponse(BaseModel):
    success: bool
    task_id: str | None
    data: dict = Field(default_factory=dict)
    confidence: float = 0.0
    processing_time_ms: int | None = None
    execution_id: UUID | None = None
