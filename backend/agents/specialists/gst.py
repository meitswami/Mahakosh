from typing import Any
import re

from backend.agents.base.types import AgentContext, AgentEventType, AgentResult
from backend.agents.communication.event_bus import event_bus
from backend.agents.specialists._base import SpecialistAgent


class GSTAgent(SpecialistAgent):
    name = "gst"
    version = "2.0.0"
    description = "GST rate detection, validation, and tax computation from knowledge"
    capabilities = ["gst_validation", "gst_rate_detection", "tax_computation"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        gstin = input_data.get("gstin", "")
        amount = float(input_data.get("total_amount") or input_data.get("amount") or 0)
        query = input_data.get("query", f"GST rate tax {gstin} invoice")

        tools, _, _ = await self._with_tools(context)
        knowledge = await tools["knowledge"].search(
            context.tenant_id, query, mode="hybrid", top_k=10,
            collection_slug="invoices", user_id=context.user_id,
        )

        gst_rate = input_data.get("gst_rate")
        if gst_rate is None:
            for r in knowledge.get("results", []):
                match = re.search(r"(\d+(?:\.\d+)?)\s*%", r.get("content", ""))
                if match:
                    gst_rate = float(match.group(1))
                    break
            if gst_rate is None:
                gst_rate = 18.0

        cgst = round(amount * (gst_rate / 100) / 2, 2)
        sgst = round(amount * (gst_rate / 100) / 2, 2)
        igst = round(amount * (gst_rate / 100), 2) if input_data.get("inter_state") else 0.0
        gstin_valid = len(gstin) == 15 if gstin else False

        confidence = 94.0 if gstin_valid and knowledge.get("total_found", 0) > 0 else 78.0

        await event_bus.broadcast(
            context.tenant_id, self.name, AgentEventType.GST_DETECTED,
            {"gst_rate": gst_rate, "gstin": gstin, "amount": amount},
        )

        return AgentResult(
            success=True,
            data={
                "gstin": gstin,
                "gstin_valid": gstin_valid,
                "gst_rate": gst_rate,
                "taxable_amount": amount,
                "cgst": cgst,
                "sgst": sgst,
                "igst": igst,
                "total_tax": cgst + sgst + igst,
                "knowledge_sources": knowledge.get("results", [])[:3],
            },
            confidence=confidence,
            reasoning=f"GST rate {gst_rate}% computed; GSTIN {'valid' if gstin_valid else 'missing/invalid'}",
            sources=knowledge.get("citations", []),
            next_agents=["hsn", "accounting"],
        )
