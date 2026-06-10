from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent


class OCRAgent(BaseAgent):
    name = "ocr"
    version = "2.0.0"
    description = "Dual-engine OCR pipeline with PaddleOCR + Surya consensus for Indian business documents"
    capabilities = [
        "text_extraction",
        "table_detection",
        "invoice_parsing",
        "dual_ocr_consensus",
        "document_classification",
        "field_extraction",
        "gst_validation",
    ]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        job_id = input_data.get("job_id")
        document_id = input_data.get("document_id")

        if not job_id and not document_id:
            return AgentResult(success=False, error="job_id or document_id is required")

        return AgentResult(
            success=True,
            data={
                "job_id": str(job_id) if job_id else None,
                "document_id": str(document_id) if document_id else None,
                "status": "use_ocr_api",
                "message": "OCR processing via POST /api/v1/ocr/process with job_id",
                "pipeline_stages": [
                    "classification", "preprocessing", "ocr_paddle", "ocr_surya",
                    "ocr_consensus", "layout_analysis", "table_extraction",
                    "field_extraction", "validation", "confidence_scoring", "knowledge_building",
                ],
            },
            next_agents=["validation"],
        )
