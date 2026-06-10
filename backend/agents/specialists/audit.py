from typing import Any

from backend.agents.base.types import AgentContext, AgentResult
from backend.agents.specialists._base import SpecialistAgent


class AuditAgent(SpecialistAgent):
    name = "audit"
    version = "2.0.0"
    description = "Audit trail analysis and compliance verification via knowledge retrieval"
    capabilities = ["audit_trail", "compliance_check", "anomaly_detection"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        entity_type = input_data.get("entity_type", "voucher")
        query = input_data.get("query", f"audit trail {entity_type} compliance history")

        tools, _, _ = await self._with_tools(context)
        audit_knowledge = await tools["knowledge"].search(
            context.tenant_id, query, mode="hybrid", top_k=15, user_id=context.user_id,
        )

        agent_results = input_data.get("agent_results", {})
        findings: list[dict[str, str]] = []
        for agent_name, result in agent_results.items():
            if isinstance(result, dict):
                conf = result.get("confidence", 100)
                if conf < 80:
                    findings.append({
                        "agent": agent_name,
                        "severity": "warning",
                        "message": f"Low confidence ({conf}%) — needs review",
                    })

        compliant = len(findings) == 0
        confidence = 97.0 if compliant and audit_knowledge.get("total_found", 0) > 0 else 72.0

        return AgentResult(
            success=compliant,
            data={
                "compliant": compliant,
                "findings": findings,
                "audit_sources": audit_knowledge.get("results", [])[:5],
                "agents_reviewed": list(agent_results.keys()) if agent_results else [],
            },
            confidence=confidence,
            reasoning=f"Audit complete: {len(findings)} findings, {audit_knowledge.get('total_found', 0)} knowledge sources",
            sources=audit_knowledge.get("citations", []),
        )
