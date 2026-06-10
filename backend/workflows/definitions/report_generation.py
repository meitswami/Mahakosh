from typing import Any

from backend.workflows.base import (
    BaseWorkflow,
    WorkflowDefinition,
    WorkflowExecutionContext,
    WorkflowStepDefinition,
)


class ReportGenerationWorkflow(BaseWorkflow):
    definition = WorkflowDefinition(
        name="Report Generation",
        workflow_type="report_generation",
        description="Generate business reports from knowledge and accounting data",
        steps=[
            WorkflowStepDefinition(name="knowledge_search", agent_name="search", order=1),
            WorkflowStepDefinition(name="report_build", agent_name="reporting", order=2),
            WorkflowStepDefinition(name="audit_logging", agent_name="audit", order=3),
        ],
    )

    async def on_start(self, context: WorkflowExecutionContext) -> dict[str, Any]:
        return {"started": True, "report_type": context.input_data.get("report_type")}

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
