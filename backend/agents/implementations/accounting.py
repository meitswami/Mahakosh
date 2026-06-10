from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent


class AccountingAgent(BaseAgent):
    name = "accounting"
    version = "1.0.0"
    description = "Generates accounting voucher drafts from processed documents"
    capabilities = ["voucher_generation", "ledger_mapping", "tally_export"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        return AgentResult(
            success=True,
            data={
                "voucher_draft_status": "ready",
                "voucher_type": input_data.get("voucher_type", "purchase"),
            },
            next_agents=["approval"],
        )
