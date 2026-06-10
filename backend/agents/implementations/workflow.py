from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent


class WorkflowAgent(BaseAgent):
    name = "workflow"
    version = "1.0.0"
    description = "Manages workflow state transitions and step execution"
    capabilities = ["workflow_management", "step_coordination", "retry_handling"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        return AgentResult(
            success=True,
            data={
                "workflow_id": str(context.workflow_id) if context.workflow_id else None,
                "action": input_data.get("action", "advance"),
                "status": "ready",
            },
        )
