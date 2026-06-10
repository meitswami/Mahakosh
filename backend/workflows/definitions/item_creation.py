from typing import Any

from backend.workflows.base import (
    BaseWorkflow,
    WorkflowDefinition,
    WorkflowExecutionContext,
    WorkflowStepDefinition,
)


class ItemCreationWorkflow(BaseWorkflow):
    definition = WorkflowDefinition(
        name="Item Creation",
        workflow_type="item_creation",
        description="Create inventory items with HSN mapping and validation",
        steps=[
            WorkflowStepDefinition(name="item_matching", agent_name="item", order=1),
            WorkflowStepDefinition(name="hsn_mapping", agent_name="hsn", order=2),
            WorkflowStepDefinition(name="data_validation", agent_name="validation", order=3),
            WorkflowStepDefinition(name="audit_logging", agent_name="audit", order=4),
        ],
    )

    async def on_start(self, context: WorkflowExecutionContext) -> dict[str, Any]:
        return {"started": True}

    async def on_step_complete(
        self,
        context: WorkflowExecutionContext,
        step: WorkflowStepDefinition,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        return {"step": step.name}

    async def on_complete(self, context: WorkflowExecutionContext) -> dict[str, Any]:
        return {"status": "completed", "results": context.step_results}

    async def on_failure(
        self,
        context: WorkflowExecutionContext,
        error: str,
        failed_step: WorkflowStepDefinition | None = None,
    ) -> dict[str, Any]:
        return {"status": "failed", "error": error}
