from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit import AuditLog
from backend.models.workflow import Workflow, WorkflowStep
from backend.workflows.base import BaseWorkflow, WorkflowExecutionContext, WorkflowStepDefinition
from backend.workflows.execution_monitor import ExecutionMonitor
from backend.workflows.states import WorkflowState
from backend.workflows.workflow_events import WorkflowEventType
from backend.workflows.workflow_registry import workflow_registry
from backend.workflows.workflow_runner import WorkflowRunner
from backend.workflows.workflow_state_manager import WorkflowStateManager
from backend.workflows.workflow_tracker import WorkflowTracker
from backend.workflows.transparency_builder import WorkflowTransparencyService

logger = structlog.get_logger(__name__)


def _ensure_registry() -> None:
    from backend.workflows.definitions import register_all_workflows

    register_all_workflows()


class WorkflowEngine:
    """Production workflow engine with tracking, retry, audit, and metrics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.tracker = WorkflowTracker(db)
        self.state_manager = WorkflowStateManager(db)
        self.runner = WorkflowRunner(db)
        self.monitor = ExecutionMonitor(db)
        self.transparency = WorkflowTransparencyService(db)
        _ensure_registry()

    def register(self, workflow: BaseWorkflow) -> None:
        workflow_registry.register(type(workflow))

    def get_workflow(self, workflow_type: str) -> BaseWorkflow:
        return workflow_registry.get(workflow_type)

    async def create_workflow_record(
        self,
        tenant_id: UUID,
        user_id: UUID,
        workflow_type: str,
        name: str,
        input_data: dict[str, Any],
        entity_type: str | None = None,
        entity_id: UUID | None = None,
    ) -> Workflow:
        wf_impl = self.get_workflow(workflow_type)
        agents = [s.agent_name for s in wf_impl.definition.steps]

        workflow = Workflow(
            tenant_id=tenant_id,
            name=name,
            workflow_type=workflow_type,
            status=WorkflowState.PENDING.value,
            input_data=input_data,
            created_by=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            assigned_agents=agents,
        )
        self.db.add(workflow)
        await self.db.flush()

        for step_def in wf_impl.definition.steps:
            step = WorkflowStep(
                tenant_id=tenant_id,
                workflow_id=workflow.id,
                step_name=step_def.name,
                step_order=step_def.order,
                agent_name=step_def.agent_name,
                node_type=workflow_registry.get_step_node_type(step_def.agent_name),
                step_type=step_def.agent_name,
                status=WorkflowState.PENDING.value,
            )
            self.db.add(step)

        await self.db.flush()
        await self.tracker.event(
            WorkflowEventType.WORKFLOW_CREATED,
            workflow.id,
            tenant_id,
            payload={"name": name, "workflow_type": workflow_type},
            user_id=user_id,
        )
        await self._audit(tenant_id, user_id, "workflow_created", workflow.id, {"name": name})
        return workflow

    async def execute_workflow(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        workflow_record = await self._get_workflow(workflow_id, tenant_id)
        if workflow_record.status in (WorkflowState.COMPLETED.value, WorkflowState.CANCELLED.value):
            raise ValueError(f"Workflow {workflow_id} is already {workflow_record.status}")

        self.state_manager.transition(workflow_record, WorkflowState.QUEUED)
        self.state_manager.transition(workflow_record, WorkflowState.RUNNING)

        wf_impl = self.get_workflow(workflow_record.workflow_type)
        context = WorkflowExecutionContext(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            user_id=user_id,
            input_data=workflow_record.input_data,
        )

        await self.tracker.event(
            WorkflowEventType.WORKFLOW_STARTED,
            workflow_id,
            tenant_id,
            user_id=user_id,
        )
        await wf_impl.on_start(context)
        output: dict[str, Any] = {}
        failed_step: WorkflowStepDefinition | None = None

        try:
            for step_def in wf_impl.definition.steps:
                step_result = await self.runner.execute_step(
                    workflow_record, step_def, context, tenant_id, user_id
                )
                if step_result.requires_manual_review:
                    self.state_manager.transition(workflow_record, WorkflowState.WAITING)
                    manifest = await self.transparency.build_and_persist(workflow_record)
                    await self.db.flush()
                    return {
                        "workflow_id": str(workflow_id),
                        "status": workflow_record.status,
                        "waiting_for": "manual_review",
                        "failed_step": step_def.name,
                        "transparency": manifest,
                    }
                if not step_result.success:
                    failed_step = step_def
                    raise RuntimeError(step_result.error or f"Step '{step_def.name}' failed")

                context.step_results[step_def.name] = step_result.data
                await wf_impl.on_step_complete(context, step_def, step_result.data)
                wf_impl.advance_step(context)

            output = await wf_impl.on_complete(context)
            self.state_manager.transition(workflow_record, WorkflowState.COMPLETED)
            workflow_record.output_data = output
            await self.tracker.event(
                WorkflowEventType.WORKFLOW_COMPLETED,
                workflow_id,
                tenant_id,
                payload={"output_keys": list(output.keys())},
                user_id=user_id,
            )
            await self._audit(tenant_id, user_id, "workflow_completed", workflow_id, output)
            from backend.platform.usage_tracker import UsageTracker
            await UsageTracker(self.db).record(tenant_id, "workflow_runs")

        except Exception as exc:
            logger.error("workflow_execution_failed", workflow_id=str(workflow_id), error=str(exc))
            self.state_manager.transition(workflow_record, WorkflowState.FAILED)
            workflow_record.error_message = str(exc)
            await self.tracker.event(
                WorkflowEventType.WORKFLOW_FAILED,
                workflow_id,
                tenant_id,
                payload={"error": str(exc), "failed_step": failed_step.name if failed_step else None},
                user_id=user_id,
            )
            await wf_impl.on_failure(context, str(exc), failed_step)
            await self._audit(tenant_id, user_id, "workflow_failed", workflow_id, {"error": str(exc)})

        await self.monitor.update_metrics(tenant_id, workflow_record)
        manifest = await self.transparency.build_and_persist(workflow_record)
        await self.db.flush()
        return {
            "workflow_id": str(workflow_id),
            "status": workflow_record.status,
            "output": output,
            "duration_ms": self.state_manager.duration_ms(
                workflow_record.started_at, workflow_record.completed_at
            ),
            "transparency": manifest,
        }

    async def retry_workflow(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        from_step: str | None = None,
    ) -> dict[str, Any]:
        workflow_record = await self._get_workflow(workflow_id, tenant_id)
        if workflow_record.status not in (
            WorkflowState.FAILED.value,
            WorkflowState.WAITING.value,
        ):
            raise ValueError("Only failed or waiting workflows can be retried")

        steps_result = await self.db.execute(
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == workflow_id, WorkflowStep.tenant_id == tenant_id)
            .order_by(WorkflowStep.step_order)
        )
        steps = list(steps_result.scalars().all())
        reset = from_step is None
        for step in steps:
            if reset or step.step_name == from_step:
                reset = True
                step.status = WorkflowState.PENDING.value
                step.error_message = None
                step.started_at = None
                step.completed_at = None

        workflow_record.status = WorkflowState.PENDING.value
        workflow_record.error_message = None
        workflow_record.completed_at = None
        await self.tracker.event(
            WorkflowEventType.WORKFLOW_RETRIED,
            workflow_id,
            tenant_id,
            payload={"from_step": from_step},
            user_id=user_id,
        )
        await self._audit(tenant_id, user_id, "workflow_retried", workflow_id, {"from_step": from_step})
        await self.db.flush()
        return await self.execute_workflow(workflow_id, tenant_id, user_id)

    async def cancel_workflow(self, workflow_id: UUID, tenant_id: UUID, user_id: UUID) -> WorkflowState:
        workflow_record = await self._get_workflow(workflow_id, tenant_id)
        self.state_manager.transition(workflow_record, WorkflowState.CANCELLED)
        await self.tracker.event(
            WorkflowEventType.WORKFLOW_CANCELLED,
            workflow_id,
            tenant_id,
            user_id=user_id,
        )
        await self._audit(tenant_id, user_id, "workflow_cancelled", workflow_id, {})
        await self.transparency.build_and_persist(workflow_record)
        await self.db.flush()
        return WorkflowState(workflow_record.status)

    async def _get_workflow(self, workflow_id: UUID, tenant_id: UUID) -> Workflow:
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
        )
        workflow = result.scalar_one_or_none()
        if workflow is None:
            raise ValueError(f"Workflow {workflow_id} not found")
        return workflow

    async def _audit(
        self,
        tenant_id: UUID,
        user_id: UUID,
        action: str,
        workflow_id: UUID,
        metadata: dict[str, Any],
    ) -> None:
        self.db.add(AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type="workflow",
            entity_id=workflow_id,
            metadata_=metadata,
        ))
