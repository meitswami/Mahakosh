from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.chat.types import ChatType, IntentResult
from backend.models.approval import ApprovalQueue
from backend.models.agent_swarm import AgentHealthRecord
from backend.models.workflow import Workflow


class ContextBuilder:
    """Assemble context from knowledge, workflows, agents, and chat history."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build(
        self,
        tenant_id: UUID,
        user_id: UUID,
        query: str,
        intent: IntentResult,
        knowledge_context: str,
        knowledge_citations: list[dict],
        history: list[dict[str, str]],
        agent_outputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sections: list[str] = []
        metadata: dict[str, Any] = {
            "chat_type": intent.chat_type.value,
            "intent": intent.intent.value,
            "entities": intent.entities,
        }

        if history:
            recent = history[-6:]
            hist_text = "\n".join(f"{m['role']}: {m['content']}" for m in recent)
            sections.append(f"## Conversation History\n{hist_text}")

        if knowledge_context:
            sections.append(f"## Knowledge Base Context\n{knowledge_context}")

        if agent_outputs:
            sections.append(f"## Agent Outputs\n{self._format_agent_outputs(agent_outputs)}")

        if intent.chat_type == ChatType.WORKFLOW:
            wf_ctx = await self._workflow_context(tenant_id)
            sections.append(f"## Workflow Context\n{wf_ctx}")

        if intent.chat_type == ChatType.AGENT:
            agent_ctx = await self._agent_context(tenant_id)
            sections.append(f"## Agent Status\n{agent_ctx}")

        if intent.chat_type == ChatType.ACCOUNTING:
            acct_ctx = await self._accounting_context(tenant_id, intent)
            sections.append(f"## Accounting Context\n{acct_ctx}")

        if knowledge_citations:
            cite_lines = [
                f"- {c.get('source_document')} (p.{c.get('page_number', 'N/A')}, {c.get('confidence_display', '')})"
                for c in knowledge_citations[:5]
            ]
            sections.append("## Sources\n" + "\n".join(cite_lines))

        return {
            "full_context": "\n\n".join(sections),
            "metadata": metadata,
            "token_estimate": sum(len(s.split()) for s in sections),
        }

    async def _workflow_context(self, tenant_id: UUID) -> str:
        pending = await self.db.execute(
            select(ApprovalQueue)
            .where(ApprovalQueue.tenant_id == tenant_id, ApprovalQueue.status == "pending")
            .limit(10)
        )
        approvals = pending.scalars().all()

        workflows = await self.db.execute(
            select(Workflow)
            .where(Workflow.tenant_id == tenant_id)
            .order_by(Workflow.created_at.desc())
            .limit(10)
        )
        wfs = workflows.scalars().all()

        lines = [f"Pending approvals: {len(approvals)}"]
        for a in approvals[:5]:
            lines.append(f"  - {a.title} ({a.action})")
        lines.append(f"Recent workflows: {len(wfs)}")
        for w in wfs[:5]:
            lines.append(f"  - {w.name}: {w.status}")
        return "\n".join(lines)

    async def _agent_context(self, tenant_id: UUID) -> str:
        result = await self.db.execute(
            select(AgentHealthRecord).where(AgentHealthRecord.tenant_id == tenant_id)
        )
        agents = result.scalars().all()
        if not agents:
            return "No agent execution history yet."
        return "\n".join(
            f"- {a.agent_name}: {a.status}, {a.success_rate}% success, {a.execution_count} runs"
            for a in agents
        )

    async def _accounting_context(self, tenant_id: UUID, intent: IntentResult) -> str:
        filters = intent.filters
        vendor = intent.entities.get("vendor_name", "")
        return f"Accounting query scope: vendor={vendor or 'all'}, filters={filters}"

    def _format_agent_outputs(self, outputs: dict[str, Any]) -> str:
        lines = []
        for agent, data in outputs.items():
            if isinstance(data, dict):
                summary = data.get("reasoning") or str(data.get("result", data))[:200]
                lines.append(f"### {agent}\n{summary}")
        return "\n".join(lines)
