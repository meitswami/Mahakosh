from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent


class ItemAgent(BaseAgent):
    name = "item"
    version = "1.0.0"
    description = "Identifies and matches line items from invoices and documents"
    capabilities = ["item_matching", "alias_resolution", "hsn_suggestion"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        return AgentResult(
            success=True,
            data={
                "item_match_status": "ready",
                "matched_items": [],
                "unmatched_items": [],
            },
            next_agents=["hsn"],
        )
