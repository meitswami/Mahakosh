from typing import Any

from backend.workflows.base import (
    BaseWorkflow,
    WorkflowDefinition,
    WorkflowExecutionContext,
    WorkflowStepDefinition,
)


class DocumentProcessingWorkflow(BaseWorkflow):
    definition = WorkflowDefinition(
        name="Document Processing",
        workflow_type="document_processing",
        description="End-to-end document ingestion, OCR, validation, and voucher generation",
        steps=[
            WorkflowStepDefinition(name="ocr_extraction", agent_name="ocr", order=1),
            WorkflowStepDefinition(name="data_validation", agent_name="validation", order=2),
            WorkflowStepDefinition(name="vendor_matching", agent_name="vendor", order=3),
            WorkflowStepDefinition(name="item_matching", agent_name="item", order=4),
            WorkflowStepDefinition(name="gst_validation", agent_name="gst", order=5),
            WorkflowStepDefinition(name="hsn_mapping", agent_name="hsn", order=6),
            WorkflowStepDefinition(name="voucher_generation", agent_name="accounting", order=7),
            WorkflowStepDefinition(name="approval_routing", agent_name="approval", order=8),
            WorkflowStepDefinition(name="audit_logging", agent_name="audit", order=9),
        ],
    )

    async def on_start(self, context: WorkflowExecutionContext) -> dict[str, Any]:
        return {"started": True, "document_id": context.input_data.get("document_id")}

    async def on_step_complete(
        self,
        context: WorkflowExecutionContext,
        step: WorkflowStepDefinition,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        return {"step": step.name, "completed": True}

    async def on_complete(self, context: WorkflowExecutionContext) -> dict[str, Any]:
        return {
            "status": "completed",
            "steps_executed": len(context.step_results),
            "results": context.step_results,
        }

    async def on_failure(
        self,
        context: WorkflowExecutionContext,
        error: str,
        failed_step: WorkflowStepDefinition | None = None,
    ) -> dict[str, Any]:
        return {
            "status": "failed",
            "error": error,
            "failed_step": failed_step.name if failed_step else None,
            "completed_steps": list(context.step_results.keys()),
        }
