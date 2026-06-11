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
        description="Export accounting vouchers to Tally via universal connector layer",
        steps=[
            WorkflowStepDefinition(name="voucher_generation", agent_name="accounting", order=1),
            WorkflowStepDefinition(name="validation_gate", agent_name="accounting", order=2),
            WorkflowStepDefinition(name="tally_export", agent_name="tally", order=3),
            WorkflowStepDefinition(name="audit_logging", agent_name="audit", order=4),
        ],
    )

    async def on_start(self, context: WorkflowExecutionContext) -> dict[str, Any]:
        return {
            "started": True,
            "pipeline": "draft → validation → approval → export",
            "connector_layer": "accounting_connectors",
        }

    async def on_step_complete(
        self,
        context: WorkflowExecutionContext,
        step: WorkflowStepDefinition,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if step.name == "tally_export" and result.get("export_ready"):
            context.metadata["connector_export_ready"] = True
        return {"step": step.name, "connector_layer": True}

    async def on_complete(self, context: WorkflowExecutionContext) -> dict[str, Any]:
        tally_result = context.step_results.get("tally_export", {})
        return {
            "status": "completed",
            "results": context.step_results,
            "export_ready": tally_result.get("export_ready", False),
            "connector_layer": "accounting",
        }

    async def on_failure(
        self,
        context: WorkflowExecutionContext,
        error: str,
        failed_step: WorkflowStepDefinition | None = None,
    ) -> dict[str, Any]:
        return {"status": "failed", "error": error, "failed_step": failed_step.name if failed_step else None}
