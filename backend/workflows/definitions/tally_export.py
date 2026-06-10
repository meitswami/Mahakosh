from typing import Any

from backend.workflows.base import (
    BaseWorkflow,
    WorkflowDefinition,
    WorkflowExecutionContext,
    WorkflowStepDefinition,
)


class TallyExportWorkflow(BaseWorkflow):
    definition = WorkflowDefinition(
        name="Tally Export",
        workflow_type="tally_export",
        description="Export accounting vouchers to Tally format",
        steps=[
            WorkflowStepDefinition(name="voucher_generation", agent_name="accounting", order=1),
            WorkflowStepDefinition(name="tally_export", agent_name="tally", order=2),
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
