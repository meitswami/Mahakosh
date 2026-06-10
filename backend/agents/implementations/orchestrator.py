from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.agents.registry import agent_registry


class MasterOrchestratorAgent(BaseAgent):
    name = "master_orchestrator"
    version = "1.0.0"
    description = "Coordinates agent swarm execution and task decomposition"
    capabilities = ["orchestration", "task_decomposition", "agent_routing"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        task_type = input_data.get("task_type", "general")
        payload = input_data.get("payload", {})

        routing_map: dict[str, list[str]] = {
            "document_processing": ["ocr", "validation", "vendor", "item", "gst", "hsn", "accounting"],
            "gst_validation": ["gst", "validation"],
            "report_generation": ["search", "reporting"],
            "approval_flow": ["validation", "approval", "audit"],
            "general": ["search"],
        }

        agent_chain = routing_map.get(task_type, routing_map["general"])
        results: dict[str, Any] = {}
        errors: list[str] = []

        for agent_name in agent_chain:
            try:
                agent = agent_registry.get_instance(agent_name, self.model_name)
                agent_result = await agent.run(payload, context)
                results[agent_name] = agent_result.data
                if not agent_result.success:
                    errors.append(f"{agent_name}: {agent_result.error}")
            except KeyError:
                errors.append(f"Agent '{agent_name}' not available")

        return AgentResult(
            success=len(errors) == 0,
            data={"task_type": task_type, "agent_results": results},
            error="; ".join(errors) if errors else None,
            next_agents=[],
        )
