from typing import Any

from backend.agents.base.types import AgentContext, AgentEventType, AgentResult
from backend.agents.communication.event_bus import event_bus
from backend.agents.specialists._base import SpecialistAgent


class VendorAgent(SpecialistAgent):
    name = "vendor"
    version = "2.0.0"
    description = "Matches and resolves vendor entities from knowledge base"
    capabilities = ["vendor_matching", "vendor_resolution", "duplicate_detection"]
    requires_approval_for: list[str] = []

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        vendor_name = input_data.get("vendor_name", "")
        gstin = input_data.get("gstin", "")
        query = vendor_name or gstin or input_data.get("query", "vendor supplier")
        if not query:
            return AgentResult(success=False, error="vendor_name, gstin, or query required", confidence=0.0)

        tools, _, _ = await self._with_tools(context)
        results = await tools["knowledge"].search(
            context.tenant_id,
            f"vendor {query}",
            mode="hybrid",
            top_k=10,
            filters={"document_type": "invoice"} if not gstin else None,
            collection_slug="vendors",
            user_id=context.user_id,
        )

        matched = None
        match_confidence = 0.0
        for r in results.get("results", []):
            meta = r.get("metadata", {})
            doc_gstin = meta.get("gstin") or r.get("content", "")
            if gstin and gstin in str(doc_gstin):
                matched = r
                match_confidence = min(r["score"] * 100, 98.0)
                break
            if vendor_name and vendor_name.lower() in r.get("content", "").lower():
                matched = r
                match_confidence = min(r["score"] * 100, 95.0)
                break

        if matched:
            await event_bus.broadcast(
                context.tenant_id, self.name, AgentEventType.VENDOR_MATCHED,
                {"vendor_name": vendor_name or gstin, "document_id": matched["document_id"]},
            )

        return AgentResult(
            success=matched is not None,
            data={
                "vendor_name": vendor_name,
                "gstin": gstin,
                "matched": matched,
                "candidates": results.get("results", [])[:5],
                "vendor_name_resolved": matched["document_title"] if matched else vendor_name,
            },
            confidence=match_confidence if matched else 55.0,
            reasoning=f"Vendor match {'found' if matched else 'not found'} for '{query}'",
            sources=results.get("citations", []),
            next_agents=["item", "gst"],
        )
