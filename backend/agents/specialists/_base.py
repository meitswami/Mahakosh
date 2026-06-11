from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base.agent import BaseAgent
from backend.agents.base.types import AgentContext
from backend.agents.tools.accounting_tool import AccountingTool
from backend.agents.tools.approval_tool import ApprovalTool
from backend.agents.tools.knowledge_tool import KnowledgeTool
from backend.agents.tools.workflow_tool import WorkflowTool
from backend.core.database import async_session_factory


class SpecialistAgent(BaseAgent):
    """Base for domain agents that consume data only through tools."""

    def _get_db(self, context: AgentContext) -> AsyncSession | None:
        return context.metadata.get("db")

    async def _with_tools(self, context: AgentContext):
        db = self._get_db(context)
        owns_session = False
        if db is None:
            db = async_session_factory()
            owns_session = True
            context.metadata["db"] = db

        tools = {
            "knowledge": KnowledgeTool(db),
            "workflow": WorkflowTool(db),
            "approval": ApprovalTool(db),
            "accounting": AccountingTool(db),
        }
        return tools, db, owns_session

    async def _recall(
        self,
        context: AgentContext,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> dict[str, Any]:
        tools, _, _ = await self._with_tools(context)
        return await tools["knowledge"].search(
            context.tenant_id, query, top_k=top_k, filters=filters, user_id=context.user_id
        )
