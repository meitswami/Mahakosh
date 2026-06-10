from backend.workflows.definitions.approval_flow import ApprovalFlowWorkflow
from backend.workflows.definitions.document_processing import DocumentProcessingWorkflow
from backend.workflows.definitions.gst_validation import GSTValidationWorkflow
from backend.workflows.definitions.item_creation import ItemCreationWorkflow
from backend.workflows.definitions.report_generation import ReportGenerationWorkflow
from backend.workflows.definitions.tally_export import TallyExportWorkflow
from backend.workflows.definitions.vendor_onboarding import VendorOnboardingWorkflow
from backend.workflows.workflow_registry import workflow_registry

ALL_WORKFLOWS = [
    DocumentProcessingWorkflow,
    GSTValidationWorkflow,
    ApprovalFlowWorkflow,
    ReportGenerationWorkflow,
    VendorOnboardingWorkflow,
    ItemCreationWorkflow,
    TallyExportWorkflow,
]


def register_all_workflows() -> None:
    for wf_cls in ALL_WORKFLOWS:
        if wf_cls.definition.workflow_type not in workflow_registry._workflows:
            workflow_registry.register(wf_cls)


__all__ = [
    "ALL_WORKFLOWS",
    "ApprovalFlowWorkflow",
    "DocumentProcessingWorkflow",
    "GSTValidationWorkflow",
    "ItemCreationWorkflow",
    "ReportGenerationWorkflow",
    "TallyExportWorkflow",
    "VendorOnboardingWorkflow",
    "register_all_workflows",
]
