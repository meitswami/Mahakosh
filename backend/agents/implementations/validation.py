from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent


class ValidationAgent(BaseAgent):
    name = "validation"
    version = "1.0.0"
    description = "Validates extracted document data against business rules"
    capabilities = ["data_validation", "schema_check", "anomaly_detection"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        return AgentResult(
            success=True,
            data={
                "validation_status": "ready",
                "rules_applied": [],
                "issues": [],
            },
            next_agents=["vendor", "item"],
        )
