from typing import Any
from uuid import UUID

from backend.agents.base.types import AgentContext, AgentEventType, AgentResult
from backend.agents.communication.event_bus import event_bus
from backend.agents.specialists._base import SpecialistAgent


class ApprovalAgent(SpecialistAgent):
    name = "approval"
    version = "2.0.0"
    description = "Human-in-the-loop approval queue management"
    capabilities = ["approval_routing", "pending_review", "approval_status"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        action = input_data.get("action", "list_pending")
        tools, _, _ = await self._with_tools(context)

        if action == "list_pending":
            pending = await tools["approval"].list_pending(context.tenant_id)
            return AgentResult(
                success=True,
                data={"pending_approvals": pending, "count": len(pending)},
                confidence=100.0,
                reasoning=f"{len(pending)} approvals pending review",
            )

        approval_id = input_data.get("approval_id")
        if action == "status" and approval_id:
            status = await tools["approval"].get_status(context.tenant_id, UUID(str(approval_id)))
            if not status:
                return AgentResult(success=False, error="Approval not found", confidence=0.0)
            return AgentResult(success=True, data=status, confidence=100.0, reasoning="Approval status retrieved")

        if action == "request" and context.user_id:
            from uuid import uuid4
            entity_id = input_data.get("entity_id", str(uuid4()))
            req = await tools["approval"].create_request(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                entity_type=input_data.get("entity_type", "general"),
                entity_id=UUID(str(entity_id)),
                action=input_data.get("approval_action", "general"),
                title=input_data.get("title", "Approval Required"),
                description=input_data.get("description"),
                data=input_data.get("data", {}),
                priority=input_data.get("priority", "normal"),
            )
            await event_bus.broadcast(
                context.tenant_id, self.name, AgentEventType.APPROVAL_REQUIRED, req,
            )
            return AgentResult(
                success=True,
                data=req,
                confidence=100.0,
                reasoning="Approval request created — awaiting human review",
            )

        return AgentResult(success=False, error="Invalid approval action", confidence=0.0)
