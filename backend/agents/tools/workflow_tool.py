"""Workflow access layer — agents trigger and monitor workflows through this tool only."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.workflow import Workflow, WorkflowStep
from backend.workflows.definitions.document_processing import DocumentProcessingWorkflow
from backend.workflows.engine import WorkflowEngine


class WorkflowTool:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._engine = WorkflowEngine(db)
        if "document_processing" not in self._engine._workflows:
            self._engine.register(DocumentProcessingWorkflow())

    async def create_workflow(
        self,
        tenant_id: UUID,
        user_id: UUID,
        workflow_type: str,
        name: str,
        input_data: dict[str, Any],
        entity_type: str | None = None,
        entity_id: UUID | None = None,
    ) -> dict[str, Any]:
        workflow = await self._engine.create_workflow_record(
            tenant_id=tenant_id,
            user_id=user_id,
            workflow_type=workflow_type,
            name=name,
            input_data=input_data,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        return {"workflow_id": str(workflow.id), "status": workflow.status, "name": workflow.name}

    async def execute_workflow(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        return await self._engine.execute_workflow(workflow_id, tenant_id, user_id)

    async def get_workflow(self, tenant_id: UUID, workflow_id: UUID) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            return None

        steps_result = await self.db.execute(
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == workflow_id)
            .order_by(WorkflowStep.step_order)
        )
        steps = steps_result.scalars().all()

        return {
            "id": str(workflow.id),
            "name": workflow.name,
            "workflow_type": workflow.workflow_type,
            "status": workflow.status,
            "input_data": workflow.input_data,
            "output_data": workflow.output_data,
            "steps": [
                {
                    "id": str(s.id),
                    "name": s.step_name,
                    "agent_name": s.agent_name,
                    "status": s.status,
                    "order": s.step_order,
                    "output_data": s.output_data,
                }
                for s in steps
            ],
        }

    async def cancel_workflow(self, workflow_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        return await self._engine.cancel_workflow(workflow_id, tenant_id)
