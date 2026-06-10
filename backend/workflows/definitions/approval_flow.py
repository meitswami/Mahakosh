from typing import Any

from backend.workflows.base import (
    BaseWorkflow,
    WorkflowDefinition,
    WorkflowExecutionContext,
    WorkflowStepDefinition,
)


class ApprovalFlowWorkflow(BaseWorkflow):
    definition = WorkflowDefinition(
        name="Approval Flow",
        workflow_type="approval_flow",
        description="Route items through validation and approval gates",
        steps=[
            WorkflowStepDefinition(name="data_validation", agent_name="validation", order=1),
            WorkflowStepDefinition(name="approval_routing", agent_name="approval", order=2),
            WorkflowStepDefinition(name="audit_logging", agent_name="audit", order=3),
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
