from typing import Any

from backend.agents.tools.model_router import ModelTask, model_router
from backend.chat.types import ChatIntent, IntentResult
from backend.services.llm_service import llm_service


REASONING_PROMPTS: dict[ChatIntent, str] = {
    ChatIntent.ANALYTICAL: (
        "Analyze the data. Provide trends, comparisons, and actionable insights. "
        "Use numbers from context. Structure with bullet points."
    ),
    ChatIntent.ACCOUNTING_QUERY: (
        "Answer the accounting question with specific figures from context. "
        "Format currency in Indian Rupees (₹). Highlight GST amounts where relevant."
    ),
    ChatIntent.REPORT: (
        "Generate a structured report summary with key metrics, top items, and recommendations."
    ),
    ChatIntent.DOCUMENT_QUERY: (
        "Answer based on document content. Cite specific invoices and amounts."
    ),
    ChatIntent.WORKFLOW_QUERY: (
        "Summarize workflow and approval status clearly. List pending items."
    ),
    ChatIntent.SEARCH: (
        "Present search results clearly with key findings from retrieved knowledge."
    ),
}


class ReasoningEngine:
    """LLM-powered reasoning for summaries, comparisons, analysis, trends, recommendations."""

    async def reason(
        self,
        query: str,
        context: str,
        intent: IntentResult,
        history: list[dict[str, str]] | None = None,
    ) -> tuple[str, str]:
        model = model_router.select_model(
            ModelTask.REASONING if intent.intent == ChatIntent.ANALYTICAL else ModelTask.GENERAL
        )
        instruction = REASONING_PROMPTS.get(
            intent.intent,
            "Answer the user's question using the provided context. Be concise and accurate.",
        )

        system = (
            "You are Mahakosh AI — an intelligent business assistant for Indian businesses. "
            "ज्ञान से निर्णय तक. Answer in clear English (Hindi terms for GST/business ok). "
            f"{instruction} "
            "If context is insufficient, state what is missing. Never invent financial figures."
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        if context:
            messages.append({"role": "system", "content": f"Context:\n\n{context[:12000]}"})
        if history:
            for msg in history[-8:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": query})

        answer = await llm_service.chat_completion(messages, model=model)
        return answer, model

    async def extract_structured_data(
        self,
        query: str,
        intent: IntentResult,
        retrieval: dict[str, Any],
    ) -> dict[str, Any]:
        structured: dict[str, Any] = {}
        results = retrieval.get("results", [])
        citations = retrieval.get("citations", [])

        if intent.intent == ChatIntent.ACCOUNTING_QUERY:
            amounts = []
            vendors: dict[str, float] = {}
            for r in results:
                content = r.content if hasattr(r, "content") else r.get("content", "")
                meta = r.metadata if hasattr(r, "metadata") else r.get("metadata", {})
                amt = meta.get("amount")
                vendor = meta.get("vendor_name") or r.document_title if hasattr(r, "document_title") else r.get("document_title", "")
                if amt:
                    amounts.append(float(amt))
                    if vendor:
                        vendors[vendor] = vendors.get(vendor, 0) + float(amt)
            if amounts:
                structured["total_purchases"] = sum(amounts)
                structured["invoice_count"] = len(amounts)
            if vendors:
                top = max(vendors, key=vendors.get)
                structured["top_vendor"] = top
                structured["top_vendor_amount"] = vendors[top]

        if citations:
            confs = [c.get("confidence", 0) for c in citations if isinstance(c, dict)]
            if confs:
                structured["confidence"] = round(sum(confs) / len(confs), 1)

        return structured
