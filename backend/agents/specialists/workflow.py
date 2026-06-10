from typing import Any
from uuid import UUID

from backend.agents.base.types import AgentContext, AgentEventType, AgentResult
from backend.agents.communication.event_bus import event_bus
from backend.agents.specialists._base import SpecialistAgent


class WorkflowAgent(SpecialistAgent):
    name = "workflow"
    version = "2.0.0"
    description = "Manages workflow lifecycle through Workflow API"
    capabilities = ["workflow_create", "workflow_execute", "workflow_monitor"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        action = input_data.get("action", "status")
        tools, _, _ = await self._with_tools(context)

        if action == "create" and context.user_id:
            wf = await tools["workflow"].create_workflow(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                workflow_type=input_data.get("workflow_type", "document_processing"),
                name=input_data.get("name", "Agent Workflow"),
                input_data=input_data.get("input_data", input_data),
            )
            return AgentResult(success=True, data=wf, confidence=95.0, reasoning="Workflow created")

        workflow_id = input_data.get("workflow_id")
        if action == "execute" and workflow_id and context.user_id:
            result = await tools["workflow"].execute_workflow(
                UUID(str(workflow_id)), context.tenant_id, context.user_id,
            )
            await event_bus.broadcast(
                context.tenant_id, self.name, AgentEventType.WORKFLOW_COMPLETED,
                {"workflow_id": workflow_id},
            )
            return AgentResult(success=True, data=result, confidence=90.0, reasoning="Workflow executed")

        if workflow_id:
            status = await tools["workflow"].get_workflow(context.tenant_id, UUID(str(workflow_id)))
            if status:
                return AgentResult(success=True, data=status, confidence=100.0, reasoning="Workflow status retrieved")
            return AgentResult(success=False, error="Workflow not found", confidence=0.0)

        return AgentResult(success=False, error="workflow_id or create action required", confidence=0.0)
