from typing import Any
from uuid import uuid4

from backend.agents.base.types import AgentContext, AgentResult
from backend.agents.specialists._base import SpecialistAgent
from backend.agents.tools.approval_tool import ApprovalTool


class AccountingAgent(SpecialistAgent):
    name = "accounting"
    version = "2.0.0"
    description = "Drafts accounting entries from knowledge — voucher creation requires approval"
    capabilities = ["voucher_drafting", "ledger_mapping", "double_entry"]
    requires_approval_for: list[str] = ["voucher_create", "ledger_create"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        amount = float(input_data.get("total_amount") or input_data.get("amount") or 0)
        vendor = input_data.get("vendor_name", "Unknown Vendor")
        gst_rate = float(input_data.get("gst_rate", 18))
        document_type = input_data.get("document_type", "purchase_invoice")

        tools, _, _ = await self._with_tools(context)
        knowledge = await tools["knowledge"].search(
            context.tenant_id,
            f"accounting voucher ledger {document_type} {vendor}",
            mode="hybrid",
            top_k=10,
            user_id=context.user_id,
        )

        tax = round(amount * gst_rate / 100, 2)
        voucher_draft = {
            "voucher_type": "purchase" if "purchase" in document_type else "sales",
            "party": vendor,
            "amount": amount,
            "tax": tax,
            "total": round(amount + tax, 2),
            "lines": [
                {"ledger": "Purchase Account", "debit": amount, "credit": 0},
                {"ledger": "Input CGST", "debit": tax / 2, "credit": 0},
                {"ledger": "Input SGST", "debit": tax / 2, "credit": 0},
                {"ledger": vendor, "debit": 0, "credit": round(amount + tax, 2)},
            ],
        }

        approval = None
        if context.user_id and ApprovalTool.requires_approval("voucher_create"):
            approval = await tools["approval"].create_request(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                entity_type="voucher",
                entity_id=uuid4(),
                action="voucher_create",
                title=f"Voucher draft — {vendor} ₹{voucher_draft['total']:,.2f}",
                description="Voucher creation requires human approval before posting",
                data=voucher_draft,
                priority="high",
            )

        return AgentResult(
            success=True,
            data={
                "voucher_draft": voucher_draft,
                "approval": approval,
                "pending_approval": approval is not None,
                "knowledge_context": knowledge.get("results", [])[:3],
            },
            confidence=91.0 if knowledge.get("total_found", 0) > 0 else 75.0,
            reasoning=f"Drafted {voucher_draft['voucher_type']} voucher for ₹{voucher_draft['total']:,.2f}",
            sources=knowledge.get("citations", []),
            next_agents=["approval", "tally"],
        )
