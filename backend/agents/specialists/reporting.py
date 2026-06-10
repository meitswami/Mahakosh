from typing import Any

from backend.agents.base.types import AgentContext, AgentResult
from backend.agents.specialists._base import SpecialistAgent
from backend.agents.tools.model_router import ModelTask, model_router
from backend.services.llm_service import llm_service


class ReportingAgent(SpecialistAgent):
    name = "reporting"
    version = "2.0.0"
    description = "Generates business intelligence reports from knowledge retrieval"
    capabilities = ["report_generation", "data_aggregation", "insight_summarization"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        report_type = input_data.get("report_type", "summary")
        query = input_data.get("query", f"business report {report_type} invoices GST accounting")

        tools, _, _ = await self._with_tools(context)
        context_data = await tools["knowledge"].get_context(
            context.tenant_id, query, top_k=8,
        )

        model = self.model_name or model_router.select_model(ModelTask.SUMMARIZATION)
        summary = await llm_service.chat_completion(
            [
                {"role": "system", "content": "Generate a concise business report from the provided knowledge context."},
                {"role": "user", "content": f"Report type: {report_type}\n\nContext:\n{context_data.get('context', '')}"},
            ],
            model=model,
        )

        if not summary:
            summary = f"Report based on {len(context_data.get('chunk_ids', []))} knowledge chunks for: {query}"

        return AgentResult(
            success=True,
            data={
                "report_type": report_type,
                "summary": summary,
                "sources": context_data.get("citations", []),
                "document_ids": context_data.get("document_ids", []),
                "chunk_count": len(context_data.get("chunk_ids", [])),
            },
            confidence=88.0 if context_data.get("context") else 50.0,
            reasoning=f"Generated {report_type} report from {len(context_data.get('chunk_ids', []))} sources",
            sources=context_data.get("citations", []),
            next_agents=["audit"],
        )
