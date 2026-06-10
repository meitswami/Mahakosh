from typing import Any

from backend.agents.base.types import AgentContext, AgentEventType, AgentResult
from backend.agents.communication.event_bus import event_bus
from backend.agents.specialists._base import SpecialistAgent


class ValidationAgent(SpecialistAgent):
    name = "validation"
    version = "2.0.0"
    description = "Cross-validates extracted data against knowledge base rules"
    capabilities = ["field_validation", "consensus_validation", "compliance_check"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        fields = input_data.get("fields", input_data.get("structured_fields", {}))
        document_type = input_data.get("document_type", "invoice")
        query = input_data.get("query", f"validation rules {document_type} GST invoice fields")

        tools, _, _ = await self._with_tools(context)
        rules = await tools["knowledge"].search(
            context.tenant_id, query, mode="hybrid", top_k=10, user_id=context.user_id
        )

        issues: list[dict[str, str]] = []
        checks_passed: list[str] = []
        required = ["gstin", "invoice_number", "total_amount", "vendor_name"]
        if document_type == "invoice":
            for field in required:
                val = fields.get(field) or input_data.get(field)
                if val:
                    checks_passed.append(field)
                else:
                    issues.append({"field": field, "severity": "error", "message": f"Missing {field}"})

        gstin = fields.get("gstin") or input_data.get("gstin", "")
        if gstin and len(str(gstin)) != 15:
            issues.append({"field": "gstin", "severity": "error", "message": "GSTIN must be 15 characters"})

        is_valid = len([i for i in issues if i["severity"] == "error"]) == 0
        confidence = 96.0 if is_valid else max(40.0, 80.0 - len(issues) * 10)

        await event_bus.broadcast(
            context.tenant_id, self.name, AgentEventType.VALIDATION_COMPLETED,
            {"is_valid": is_valid, "issues_count": len(issues)},
        )

        return AgentResult(
            success=is_valid,
            data={
                "is_valid": is_valid,
                "issues": issues,
                "checks_passed": checks_passed,
                "rules_context": rules.get("results", [])[:3],
            },
            confidence=confidence,
            reasoning=f"Validated {len(checks_passed)} fields, {len(issues)} issues found",
            sources=rules.get("citations", []),
            error="; ".join(i["message"] for i in issues) if not is_valid else None,
            next_agents=["gst", "vendor"],
        )
