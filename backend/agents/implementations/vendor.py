from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent


class VendorAgent(BaseAgent):
    name = "vendor"
    version = "1.0.0"
    description = "Identifies and matches vendor information from documents"
    capabilities = ["vendor_matching", "gstin_lookup", "vendor_creation"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        return AgentResult(
            success=True,
            data={
                "vendor_match_status": "ready",
                "matched_vendor_id": None,
                "confidence": None,
            },
            next_agents=["gst"],
        )
