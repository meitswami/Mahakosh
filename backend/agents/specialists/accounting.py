from typing import Any
from uuid import uuid4

from backend.agents.base.types import AgentContext, AgentResult
from backend.agents.specialists._base import SpecialistAgent
from backend.agents.tools.approval_tool import ApprovalTool
from backend.connectors.accounting.draft.draft_engine import VoucherDraftEngine
from backend.connectors.accounting.intelligence.gst_intelligence import GSTIntelligence
from backend.connectors.accounting.validation.validator import AccountingValidator


class AccountingAgent(SpecialistAgent):
    name = "accounting"
    version = "3.0.0"
    description = "Drafts accounting entries via Universal Accounting Connector Layer"
    capabilities = ["voucher_drafting", "ledger_mapping", "double_entry", "gst_validation"]
    requires_approval_for: list[str] = ["voucher_create", "ledger_create"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        tools, _, _ = await self._with_tools(context)
        knowledge = await tools["knowledge"].search(
            context.tenant_id,
            f"accounting voucher ledger {input_data.get('document_type', 'purchase')}",
            mode="hybrid",
            top_k=10,
            user_id=context.user_id,
        )

        gst_validation = GSTIntelligence.validate_invoice(input_data)
        voucher_draft = VoucherDraftEngine.generate(input_data)
        validation = AccountingValidator.validate_voucher_draft(voucher_draft)

        approval = None
        if context.user_id and ApprovalTool.requires_approval("voucher_create"):
            approval = await tools["approval"].create_request(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                entity_type="voucher",
                entity_id=uuid4(),
                action="voucher_create",
                title=f"Voucher draft — {voucher_draft.get('party_name', 'Unknown')} ₹{voucher_draft['total_amount']:,.2f}",
                description="Voucher creation requires human approval before posting",
                data={
                    "voucher_draft": voucher_draft,
                    "validation": AccountingValidator.to_dict(validation),
                    "gst_validation": gst_validation,
                },
                priority="high",
            )

        return AgentResult(
            success=True,
            data={
                "voucher_draft": voucher_draft,
                "validation": AccountingValidator.to_dict(validation),
                "gst_validation": gst_validation,
                "approval": approval,
                "pending_approval": approval is not None,
                "knowledge_context": knowledge.get("results", [])[:3],
            },
            confidence=91.0 if validation.is_valid and knowledge.get("total_found", 0) > 0 else 75.0,
            reasoning=f"Drafted {voucher_draft['voucher_type']} voucher for ₹{voucher_draft['total_amount']:,.2f}",
            sources=knowledge.get("citations", []),
            next_agents=["approval", "tally"],
        )
