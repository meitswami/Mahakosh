from typing import Any

from backend.agents.base.types import AgentContext, AgentResult
from backend.agents.specialists._base import SpecialistAgent
from backend.agents.tools.model_router import ModelTask, model_router


class SearchAgent(SpecialistAgent):
    name = "search"
    version = "2.0.0"
    description = "Semantic and hybrid search across knowledge base"
    capabilities = ["semantic_search", "vector_retrieval", "context_ranking", "hybrid_search"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        query = input_data.get("query", "").strip()
        if not query:
            return AgentResult(success=False, error="query is required", confidence=0.0)

        mode = input_data.get("mode", "hybrid")
        top_k = int(input_data.get("top_k", 20))
        filters = input_data.get("filters")
        collection_slug = input_data.get("collection_slug")

        tools, _, _ = await self._with_tools(context)
        response = await tools["knowledge"].search(
            context.tenant_id,
            query,
            mode=mode,
            top_k=top_k,
            filters=filters,
            collection_slug=collection_slug,
            user_id=context.user_id,
        )

        avg_score = 0.0
        if response["results"]:
            avg_score = sum(r["score"] for r in response["results"]) / len(response["results"]) * 100

        return AgentResult(
            success=True,
            data=response,
            confidence=min(round(avg_score, 2), 99.0),
            reasoning=f"Retrieved {response['total_found']} results via {response['mode']} search",
            sources=response.get("citations", []),
            next_agents=["master_orchestrator"],
        )

    async def initialize(self) -> None:
        self.model_name = model_router.select_model(ModelTask.GENERAL)
        await super().initialize()
