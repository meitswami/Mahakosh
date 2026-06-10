from typing import Any

from backend.workflows.base import (
    BaseWorkflow,
    WorkflowDefinition,
    WorkflowExecutionContext,
    WorkflowStepDefinition,
)


class VendorOnboardingWorkflow(BaseWorkflow):
    definition = WorkflowDefinition(
        name="Vendor Onboarding",
        workflow_type="vendor_onboarding",
        description="Onboard new vendors with GST validation and approval",
        steps=[
            WorkflowStepDefinition(name="vendor_matching", agent_name="vendor", order=1),
            WorkflowStepDefinition(name="gst_validation", agent_name="gst", order=2),
            WorkflowStepDefinition(name="approval_routing", agent_name="approval", order=3),
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
