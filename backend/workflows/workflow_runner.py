import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base import AgentContext
from backend.agents.registry import agent_registry
from backend.models.workflow import Workflow, WorkflowStep
from backend.workflows.base import WorkflowExecutionContext, WorkflowStepDefinition
from backend.workflows.states import WorkflowState
from backend.workflows.workflow_events import WorkflowEventType
from backend.workflows.workflow_registry import workflow_registry
from backend.workflows.workflow_state_manager import WorkflowStateManager
from backend.workflows.workflow_tracker import WorkflowTracker

logger = structlog.get_logger(__name__)

FALLBACK_AGENTS: dict[str, str] = {
    "ocr": "validation",
    "validation": "audit",
    "vendor": "search",
    "item": "search",
    "gst": "validation",
    "hsn": "validation",
    "accounting": "audit",
    "approval": "audit",
    "reporting": "audit",
    "tally": "accounting",
    "search": "audit",
}


@dataclass
class StepExecutionResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    agent_name: str | None = None
    duration_ms: int | None = None
    reasoning_summary: str | None = None
    confidence: float | None = None
    used_fallback: bool = False
    requires_manual_review: bool = False


class WorkflowRunner:
    """Execute workflow steps with retry, fallback agents, and manual review routing."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tracker = WorkflowTracker(db)
        self.state_manager = WorkflowStateManager(db)

    async def execute_step(
        self,
        workflow: Workflow,
        step_def: WorkflowStepDefinition,
        context: WorkflowExecutionContext,
        tenant_id: UUID,
        user_id: UUID,
    ) -> StepExecutionResult:
        step_record = await self._get_step_record(workflow.id, step_def.name, tenant_id)
        step_record.node_type = workflow_registry.get_step_node_type(step_def.agent_name)
        step_record.step_type = step_def.agent_name

        self.state_manager.transition_step(step_record, WorkflowState.RUNNING)
        await self.tracker.event(
            WorkflowEventType.STEP_STARTED,
            workflow.id,
            tenant_id,
            payload={"step_name": step_def.name, "agent_name": step_def.agent_name},
            agent_name=step_def.agent_name,
            user_id=user_id,
        )

        last_error: str | None = None
        for attempt in range(step_def.retry_limit + 1):
            if attempt > 0:
                step_record.retry_count = attempt
                await self.tracker.event(
                    WorkflowEventType.STEP_RETRIED,
                    workflow.id,
                    tenant_id,
                    payload={"step_name": step_def.name, "attempt": attempt},
                    agent_name=step_def.agent_name,
                    user_id=user_id,
                )

            result = await self._invoke_agent(
                step_def.agent_name,
                context.input_data,
                workflow,
                step_record,
                tenant_id,
                user_id,
                step_def.timeout_seconds,
            )
            if result.success:
                step_record.output_data = result.data
                self.state_manager.transition_step(step_record, WorkflowState.COMPLETED)
                await self._persist_log(workflow, step_record, step_def, result, user_id, attempt)
                await self.tracker.event(
                    WorkflowEventType.STEP_COMPLETED,
                    workflow.id,
                    tenant_id,
                    payload={"step_name": step_def.name, "attempt": attempt},
                    agent_name=result.agent_name,
                    user_id=user_id,
                )
                return result

            last_error = result.error
            logger.warning(
                "step_attempt_failed",
                step=step_def.name,
                attempt=attempt,
                error=last_error,
            )

        fallback = FALLBACK_AGENTS.get(step_def.agent_name)
        if fallback:
            await self.tracker.event(
                WorkflowEventType.AGENT_INVOKED,
                workflow.id,
                tenant_id,
                payload={"step_name": step_def.name, "fallback_agent": fallback},
                agent_name=fallback,
                user_id=user_id,
            )
            fallback_result = await self._invoke_agent(
                fallback,
                context.input_data,
                workflow,
                step_record,
                tenant_id,
                user_id,
                step_def.timeout_seconds,
            )
            if fallback_result.success:
                fallback_result.used_fallback = True
                step_record.output_data = fallback_result.data
                self.state_manager.transition_step(step_record, WorkflowState.COMPLETED)
                await self._persist_log(workflow, step_record, step_def, fallback_result, user_id, step_record.retry_count)
                await self.tracker.event(
                    WorkflowEventType.STEP_COMPLETED,
                    workflow.id,
                    tenant_id,
                    payload={"step_name": step_def.name, "fallback": True},
                    agent_name=fallback,
                    user_id=user_id,
                )
                return fallback_result

        self.state_manager.transition_step(step_record, WorkflowState.FAILED)
        step_record.error_message = last_error
        await self.tracker.event(
            WorkflowEventType.STEP_FAILED,
            workflow.id,
            tenant_id,
            payload={"step_name": step_def.name, "error": last_error},
            agent_name=step_def.agent_name,
            user_id=user_id,
        )

        if step_def.agent_name != "approval":
            self.state_manager.transition_step(step_record, WorkflowState.WAITING)
            await self.tracker.event(
                WorkflowEventType.APPROVAL_REQUIRED,
                workflow.id,
                tenant_id,
                payload={
                    "step_name": step_def.name,
                    "reason": "manual_review_required",
                    "error": last_error,
                },
                agent_name="approval",
                user_id=user_id,
            )
            return StepExecutionResult(
                success=False,
                error=last_error,
                requires_manual_review=True,
            )

        return StepExecutionResult(success=False, error=last_error)

    async def _invoke_agent(
        self,
        agent_name: str,
        input_data: dict[str, Any],
        workflow: Workflow,
        step_record: WorkflowStep,
        tenant_id: UUID,
        user_id: UUID,
        timeout_seconds: int,
    ) -> StepExecutionResult:
        started = datetime.now(UTC)
        try:
            agent = agent_registry.get_instance(agent_name)
            agent_context = AgentContext(
                tenant_id=tenant_id,
                user_id=user_id,
                workflow_id=workflow.id,
                workflow_step_id=step_record.id,
                metadata={"db": self.db},
            )
            agent_result = await asyncio.wait_for(
                agent.run(input_data, agent_context),
                timeout=timeout_seconds,
            )
            duration = int((datetime.now(UTC) - started).total_seconds() * 1000)
            reasoning = agent_result.reasoning or agent_result.data.get("reasoning_summary") or agent_result.data.get("summary")
            confidence = agent_result.confidence or agent_result.data.get("confidence")

            output_data = dict(agent_result.data or {})
            if agent_result.sources:
                output_data["sources"] = agent_result.sources
            if agent_result.reasoning:
                output_data["reasoning"] = agent_result.reasoning
            if agent_result.confidence:
                output_data["confidence"] = agent_result.confidence

            return StepExecutionResult(
                success=agent_result.success,
                data=output_data,
                error=agent_result.error,
                agent_name=agent_name,
                duration_ms=duration,
                reasoning_summary=reasoning,
                confidence=confidence,
            )
        except TimeoutError:
            duration = int((datetime.now(UTC) - started).total_seconds() * 1000)
            return StepExecutionResult(
                success=False,
                error=f"Agent '{agent_name}' timed out after {timeout_seconds}s",
                agent_name=agent_name,
                duration_ms=duration,
            )
        except Exception as exc:
            duration = int((datetime.now(UTC) - started).total_seconds() * 1000)
            return StepExecutionResult(
                success=False,
                error=str(exc),
                agent_name=agent_name,
                duration_ms=duration,
            )

    async def _get_step_record(
        self,
        workflow_id: UUID,
        step_name: str,
        tenant_id: UUID,
    ) -> WorkflowStep:
        result = await self.db.execute(
            select(WorkflowStep).where(
                WorkflowStep.workflow_id == workflow_id,
                WorkflowStep.step_name == step_name,
                WorkflowStep.tenant_id == tenant_id,
            )
        )
        return result.scalar_one()

    async def _persist_log(
        self,
        workflow: Workflow,
        step_record: WorkflowStep,
        step_def: WorkflowStepDefinition,
        result: StepExecutionResult,
        user_id: UUID,
        attempt: int,
    ) -> None:
        await self.tracker.log_execution(
            workflow.tenant_id,
            workflow.id,
            action="step_execute",
            step_id=step_record.id,
            agent_name=result.agent_name or step_def.agent_name,
            input_data={"step_name": step_def.name, "attempt": attempt},
            output_data=result.data,
            reasoning_summary=result.reasoning_summary,
            confidence=result.confidence,
            duration_ms=result.duration_ms,
            error_message=result.error,
            user_id=user_id,
        )
