from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.workflow import Workflow, WorkflowStep
from backend.workflows.states import WorkflowState, WorkflowStateMachine


class WorkflowStateManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    def transition(self, workflow: Workflow, target: WorkflowState) -> WorkflowState:
        sm = WorkflowStateMachine(WorkflowState(workflow.status))
        sm.transition(target)
        workflow.status = sm.state.value
        if target == WorkflowState.RUNNING and not workflow.started_at:
            workflow.started_at = datetime.now(UTC)
        if sm.is_terminal():
            workflow.completed_at = datetime.now(UTC)
        return sm.state

    def transition_step(self, step: WorkflowStep, target: WorkflowState) -> None:
        step.status = target.value
        if target == WorkflowState.RUNNING:
            step.started_at = datetime.now(UTC)
        if target in (WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED):
            step.completed_at = datetime.now(UTC)

    def duration_ms(self, started_at: datetime | None, completed_at: datetime | None) -> int | None:
        if started_at and completed_at:
            return int((completed_at - started_at).total_seconds() * 1000)
        if started_at:
            return int((datetime.now(UTC) - started_at).total_seconds() * 1000)
        return None
