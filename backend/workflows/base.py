from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from backend.workflows.states import WorkflowState


@dataclass
class WorkflowStepDefinition:
    name: str
    agent_name: str
    order: int
    input_mapping: dict[str, str] = field(default_factory=dict)
    retry_limit: int = 3
    timeout_seconds: int = 300
    required: bool = True


@dataclass
class WorkflowDefinition:
    name: str
    workflow_type: str
    description: str
    steps: list[WorkflowStepDefinition]
    max_retries: int = 3
    timeout_seconds: int = 3600


@dataclass
class WorkflowExecutionContext:
    workflow_id: UUID
    tenant_id: UUID
    user_id: UUID
    input_data: dict[str, Any]
    current_step: int = 0
    step_results: dict[str, Any] = field(default_factory=dict)


class BaseWorkflow(ABC):
    definition: WorkflowDefinition

    @abstractmethod
    async def on_start(self, context: WorkflowExecutionContext) -> dict[str, Any]:
        """Called when workflow starts execution."""

    @abstractmethod
    async def on_step_complete(
        self,
        context: WorkflowExecutionContext,
        step: WorkflowStepDefinition,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Called after each step completes."""

    @abstractmethod
    async def on_complete(self, context: WorkflowExecutionContext) -> dict[str, Any]:
        """Called when all steps complete successfully."""

    @abstractmethod
    async def on_failure(
        self,
        context: WorkflowExecutionContext,
        error: str,
        failed_step: WorkflowStepDefinition | None = None,
    ) -> dict[str, Any]:
        """Called when workflow fails."""

    def get_next_step(self, context: WorkflowExecutionContext) -> WorkflowStepDefinition | None:
        if context.current_step >= len(self.definition.steps):
            return None
        return self.definition.steps[context.current_step]

    def advance_step(self, context: WorkflowExecutionContext) -> None:
        context.current_step += 1

    def get_state_for_step(self, step_index: int, total_steps: int) -> WorkflowState:
        if step_index == 0:
            return WorkflowState.RUNNING
        if step_index >= total_steps:
            return WorkflowState.COMPLETED
        return WorkflowState.RUNNING
