from typing import Any
import re

from backend.agents.base.types import AgentContext, AgentResult
from backend.agents.specialists._base import SpecialistAgent


class HSNAgent(SpecialistAgent):
    name = "hsn"
    version = "2.0.0"
    description = "HSN/SAC code classification from knowledge base"
    capabilities = ["hsn_classification", "sac_mapping", "gst_hsn_validation"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        items = input_data.get("items", input_data.get("line_items", []))
        query = input_data.get("query", "HSN SAC code classification")

        tools, _, _ = await self._with_tools(context)
        knowledge = await tools["knowledge"].search(
            context.tenant_id, query, mode="hybrid", top_k=15,
            user_id=context.user_id,
        )

        classified = []
        for item in items if isinstance(items, list) else []:
            name = item.get("name") or item.get("description", "")
            hsn = item.get("hsn_code") or item.get("hsn")
            if not hsn and name:
                item_knowledge = await tools["knowledge"].search(
                    context.tenant_id, f"HSN {name}", top_k=3, user_id=context.user_id,
                )
                for r in item_knowledge.get("results", []):
                    match = re.search(r"\b(\d{4,8})\b", r.get("content", ""))
                    if match:
                        hsn = match.group(1)
                        break
            classified.append({"item": name, "hsn_code": hsn, "classified": hsn is not None})

        classified_count = sum(1 for c in classified if c["classified"])
        total = len(classified) or 1
        confidence = round((classified_count / total) * 100, 2) if classified else 82.0

        return AgentResult(
            success=True,
            data={
                "classified_items": classified,
                "hsn_code": classified[0]["hsn_code"] if classified else input_data.get("hsn_code"),
                "knowledge_context": knowledge.get("results", [])[:5],
            },
            confidence=confidence,
            reasoning=f"Classified HSN for {classified_count}/{total} items",
            sources=knowledge.get("citations", []),
            next_agents=["accounting"],
        )
