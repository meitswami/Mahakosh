from typing import Any

from backend.agents.base.types import AgentContext, AgentEventType, AgentResult
from backend.agents.communication.event_bus import event_bus
from backend.agents.specialists._base import SpecialistAgent
from backend.agents.tools.approval_tool import ApprovalTool


class ItemAgent(SpecialistAgent):
    name = "item"
    version = "2.0.0"
    description = "Resolves line items and product mappings from knowledge base"
    capabilities = ["item_matching", "hsn_lookup", "inventory_mapping"]
    requires_approval_for: list[str] = ["item_create"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        items = input_data.get("items", input_data.get("line_items", []))
        query = input_data.get("query", "item product HSN inventory line items")
        create_new = input_data.get("create_new", False)

        tools, _, _ = await self._with_tools(context)
        knowledge = await tools["knowledge"].search(
            context.tenant_id, query, mode="hybrid", top_k=15,
            collection_slug="knowledge", user_id=context.user_id,
        )

        resolved_items = []
        for item in items if isinstance(items, list) else []:
            name = item.get("name") or item.get("description", "")
            item_results = await tools["knowledge"].search(
                context.tenant_id, f"item {name}", top_k=3, user_id=context.user_id,
            ) if name else {"results": []}
            resolved_items.append({
                "input": item,
                "matches": item_results.get("results", [])[:2],
                "resolved": bool(item_results.get("results")),
            })

        approval_required = create_new and ApprovalTool.requires_approval("item_create")
        approval_data = None
        if approval_required and context.user_id:
            from uuid import uuid4
            approval_data = await tools["approval"].create_request(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                entity_type="item",
                entity_id=uuid4(),
                action="item_create",
                title=f"Create {len(items)} new items",
                description="Item creation requires human approval",
                data={"items": items, "resolved": resolved_items},
            )

        resolved_count = sum(1 for r in resolved_items if r["resolved"])
        total = len(resolved_items) or 1
        confidence = round((resolved_count / total) * 100, 2) if resolved_items else 70.0

        await event_bus.broadcast(
            context.tenant_id, self.name, AgentEventType.ITEM_CREATED,
            {"count": len(resolved_items), "approval_required": approval_required},
        )

        return AgentResult(
            success=True,
            data={
                "resolved_items": resolved_items,
                "knowledge_context": knowledge.get("results", [])[:5],
                "approval": approval_data,
                "create_pending_approval": approval_required,
            },
            confidence=confidence,
            reasoning=f"Resolved {resolved_count}/{total} items from knowledge base",
            sources=knowledge.get("citations", []),
            next_agents=["gst", "hsn"],
        )
