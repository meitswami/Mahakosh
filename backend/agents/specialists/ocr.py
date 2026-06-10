from typing import Any
from uuid import UUID

from backend.agents.base.types import AgentContext, AgentEventType, AgentResult
from backend.agents.communication.event_bus import event_bus
from backend.agents.specialists._base import SpecialistAgent


class OCRAgent(SpecialistAgent):
    name = "ocr"
    version = "2.0.0"
    description = "Orchestrates document OCR via workflow and knowledge retrieval"
    capabilities = ["document_ocr", "workflow_trigger", "knowledge_lookup"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        document_id = input_data.get("document_id")
        query = input_data.get("query", f"OCR document {document_id}" if document_id else "invoice OCR extraction")

        tools, _, _ = await self._with_tools(context)

        if input_data.get("trigger_workflow") and context.user_id:
            wf = await tools["workflow"].create_workflow(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                workflow_type="document_processing",
                name=input_data.get("name", "OCR Document Processing"),
                input_data=input_data,
                entity_type=input_data.get("entity_type"),
                entity_id=UUID(str(document_id)) if document_id else None,
            )
            await event_bus.broadcast(
                context.tenant_id, self.name, AgentEventType.DOCUMENT_RECEIVED, wf
            )
            return AgentResult(
                success=True,
                data={"workflow": wf, "status": "workflow_created"},
                confidence=90.0,
                reasoning="Document processing workflow created for OCR pipeline",
                next_agents=["validation"],
            )

        knowledge = await tools["knowledge"].search(
            context.tenant_id,
            query,
            mode="hybrid",
            top_k=5,
            filters={"document_type": input_data.get("document_type", "invoice")},
            user_id=context.user_id,
        )

        if document_id:
            doc = await tools["knowledge"].get_document(context.tenant_id, UUID(str(document_id)))
            if doc:
                knowledge["document"] = doc

        found = knowledge.get("total_found", 0) > 0
        confidence = 92.0 if found else 45.0

        if found:
            await event_bus.broadcast(
                context.tenant_id, self.name, AgentEventType.OCR_COMPLETED,
                {"document_id": document_id, "results": knowledge["total_found"]},
            )

        return AgentResult(
            success=found or bool(input_data.get("allow_empty")),
            data=knowledge,
            confidence=confidence,
            reasoning=f"Retrieved {knowledge.get('total_found', 0)} OCR-indexed knowledge chunks",
            sources=knowledge.get("citations", []),
            error=None if found else "No OCR knowledge found — trigger workflow or index document first",
            next_agents=["validation"],
        )
