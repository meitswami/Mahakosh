from typing import Any
from uuid import uuid4

from backend.agents.base.types import AgentContext, AgentEventType, AgentResult
from backend.agents.communication.event_bus import event_bus
from backend.agents.specialists._base import SpecialistAgent
from backend.agents.tools.approval_tool import ApprovalTool
from backend.connectors.accounting.draft.draft_engine import VoucherDraftEngine
from backend.connectors.accounting.validation.validator import AccountingValidator
from backend.connectors.accounting.xml.generator import TallyXMLGenerator


class TallyAgent(SpecialistAgent):
    name = "tally"
    version = "2.0.0"
    description = "Prepares Tally export payloads via Universal Accounting Connector Layer"
    capabilities = ["tally_export", "tally_xml_generation", "tally_sync_prep"]
    requires_approval_for: list[str] = ["tally_write"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        voucher = input_data.get("voucher_draft", input_data)
        tools, db, owns_session = await self._with_tools(context)

        knowledge = await tools["knowledge"].search(
            context.tenant_id,
            "Tally export voucher XML ledger mapping",
            mode="hybrid",
            top_k=5,
            user_id=context.user_id,
        )

        if not voucher.get("lines"):
            voucher = VoucherDraftEngine.generate(voucher)

        validation = AccountingValidator.validate_voucher_draft(voucher)
        tally_xml = TallyXMLGenerator.voucher_xml(voucher)

        export_payload = {
            "envelope": tally_xml,
            "voucher_type": voucher.get("voucher_type", "Purchase"),
            "party": voucher.get("party_name", voucher.get("party", "")),
            "total": voucher.get("total_amount", voucher.get("total", 0)),
            "validation": AccountingValidator.to_dict(validation),
            "connector_layer": "universal_accounting",
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
                description="Tally write operations require human approval before export",
                data={"tally_xml": export_payload, "voucher": voucher, "validation": export_payload["validation"]},
                priority="high",
            )
        else:
            await event_bus.broadcast(
                context.tenant_id, self.name, AgentEventType.TALLY_EXPORT_READY,
                {"ready": True, "voucher_type": voucher.get("voucher_type"), "valid": validation.is_valid},
            )

        if owns_session and db:
            await db.close()

        return AgentResult(
            success=True,
            data={
                "tally_xml": export_payload,
                "export_ready": approval is None and validation.is_valid,
                "validation": export_payload["validation"],
                "approval": approval,
                "knowledge_context": knowledge.get("results", [])[:2],
            },
            confidence=89.0 if validation.is_valid else 65.0,
            reasoning="Tally XML generated via connector layer"
            + (" — pending approval" if approval else " — ready for export"),
            sources=knowledge.get("citations", []),
        )
