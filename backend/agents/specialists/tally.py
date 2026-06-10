from typing import Any
from uuid import uuid4

from backend.agents.base.types import AgentContext, AgentEventType, AgentResult
from backend.agents.communication.event_bus import event_bus
from backend.agents.specialists._base import SpecialistAgent
from backend.agents.tools.approval_tool import ApprovalTool


class TallyAgent(SpecialistAgent):
    name = "tally"
    version = "1.0.0"
    description = "Prepares Tally export payloads — write operations require approval"
    capabilities = ["tally_export", "tally_xml_generation", "tally_sync_prep"]
    requires_approval_for: list[str] = ["tally_write"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        voucher = input_data.get("voucher_draft", input_data)
        tools, _, _ = await self._with_tools(context)

        knowledge = await tools["knowledge"].search(
            context.tenant_id,
            "Tally export voucher XML ledger mapping",
            mode="hybrid",
            top_k=5,
            user_id=context.user_id,
        )

        tally_xml = {
            "envelope": {
                "header": {"version": "1", "company": input_data.get("company", "Mahakosh")},
                "body": {
                    "voucher": {
                        "vchtype": voucher.get("voucher_type", "Purchase"),
                        "party": voucher.get("party", ""),
                        "amount": voucher.get("total", 0),
                        "lines": voucher.get("lines", []),
                    }
                },
            }
        }

        approval = None
        if context.user_id and ApprovalTool.requires_approval("tally_write"):
            approval = await tools["approval"].create_request(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                entity_type="tally",
                entity_id=uuid4(),
                action="tally_write",
                title="Tally export — write operation",
                description="Tally write operations require human approval",
                data={"tally_xml": tally_xml, "voucher": voucher},
                priority="high",
            )
        else:
            await event_bus.broadcast(
                context.tenant_id, self.name, AgentEventType.TALLY_EXPORT_READY,
                {"ready": True, "voucher_type": voucher.get("voucher_type")},
            )

        return AgentResult(
            success=True,
            data={
                "tally_xml": tally_xml,
                "export_ready": approval is None,
                "approval": approval,
                "knowledge_context": knowledge.get("results", [])[:2],
            },
            confidence=89.0,
            reasoning="Tally export prepared" + (" — pending approval" if approval else " — ready for export"),
            sources=knowledge.get("citations", []),
        )
