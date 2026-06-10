import re
from typing import Any

from backend.chat.types import ChatIntent, ChatType, IntentResult


INTENT_PATTERNS: list[tuple[ChatIntent, ChatType, list[str], list[str]]] = [
    (ChatIntent.WORKFLOW_QUERY, ChatType.WORKFLOW, [
        r"pending approval", r"approval", r"workflow", r"running job", r"failed workflow",
        r"which workflows", r"show pending",
    ], ["approval", "workflow"]),
    (ChatIntent.ACCOUNTING_QUERY, ChatType.ACCOUNTING, [
        r"gst summary", r"top (vendor|customer)", r"outstanding payment", r"inventory",
        r"purchase trend", r"sales trend", r"vendor analysis", r"how much.*purchased",
        r"total purchase", r"ledger", r"voucher", r"accounting",
    ], ["gst", "accounting", "vendor"]),
    (ChatIntent.DOCUMENT_QUERY, ChatType.DOCUMENT, [
        r"invoice", r"summarize.*document", r"find.*invoice", r"compare invoice",
        r"show.*gst amount", r"document", r"ocr",
    ], ["search", "ocr"]),
    (ChatIntent.REPORT, ChatType.REPORTING, [
        r"generate.*report", r"monthly.*report", r"vendor summary", r"purchase report",
        r"export report", r"create.*summary",
    ], ["reporting", "search"]),
    (ChatIntent.ACTION, ChatType.AGENT, [
        r"process.*invoice", r"run.*workflow", r"execute", r"start.*agent",
    ], ["master_orchestrator"]),
    (ChatIntent.ANALYTICAL, ChatType.KNOWLEDGE, [
        r"compare", r"trend", r"analysis", r"insight", r"recommend", r"why", r"how much",
        r"last quarter", r"last month", r"top \d+",
    ], ["search"]),
    (ChatIntent.SEARCH, ChatType.KNOWLEDGE, [
        r"find", r"search", r"show me", r"list", r"get", r"what are",
    ], ["search"]),
]

AGENT_STATUS_PATTERNS = [
    r"agent.*status", r"agent.*health", r"what is.*agent", r"ocr agent", r"validation agent",
    r"show.*agent",
]


class IntentEngine:
    """Detect user intent and route to appropriate chat type and agents."""

    def detect(self, query: str, history: list[dict[str, str]] | None = None) -> IntentResult:
        q = query.lower().strip()
        history = history or []

        for pattern in AGENT_STATUS_PATTERNS:
            if re.search(pattern, q):
                return IntentResult(
                    intent=ChatIntent.SEARCH,
                    chat_type=ChatType.AGENT,
                    confidence=92.0,
                    agents=["search"],
                    entities=self._extract_entities(q),
                )

        best: IntentResult | None = None
        best_score = 0.0

        for intent, chat_type, patterns, agents in INTENT_PATTERNS:
            score = sum(1 for p in patterns if re.search(p, q))
            if score > best_score:
                best_score = score
                best = IntentResult(
                    intent=intent,
                    chat_type=chat_type,
                    confidence=min(70.0 + score * 10, 98.0),
                    agents=agents,
                    entities=self._extract_entities(q),
                    filters=self._build_filters(intent, q),
                )

        if best and best_score > 0:
            best = self._apply_history_context(best, history, q)
            return best

        return IntentResult(
            intent=ChatIntent.GENERAL,
            chat_type=ChatType.GENERAL,
            confidence=75.0,
            agents=["search"],
            entities=self._extract_entities(q),
        )

    def _extract_entities(self, query: str) -> dict[str, Any]:
        entities: dict[str, Any] = {}
        invoice_match = re.search(r"invoice[:\s#-]*(\d{4}[-_]?\d+|\w+[-_]\d+)", query, re.I)
        if invoice_match:
            entities["invoice_number"] = invoice_match.group(1)
        vendor_match = re.search(r"from\s+([A-Za-z][A-Za-z0-9\s&.'-]+?)(?:\s|$|,|\?)", query, re.I)
        if vendor_match:
            entities["vendor_name"] = vendor_match.group(1).strip()
        gst_match = re.search(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]Z[A-Z\d])\b", query, re.I)
        if gst_match:
            entities["gstin"] = gst_match.group(1).upper()
        if "gst" in query.lower() and "only" in query.lower():
            entities["gst_only"] = True
        return entities

    def _build_filters(self, intent: ChatIntent, query: str) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if intent in (ChatIntent.DOCUMENT_QUERY, ChatIntent.ACCOUNTING_QUERY):
            if "invoice" in query.lower():
                filters["document_type"] = "invoice"
            if "gst" in query.lower():
                filters.setdefault("tags", []).append("gst")
        return filters

    def _apply_history_context(
        self,
        result: IntentResult,
        history: list[dict[str, str]],
        query: str,
    ) -> IntentResult:
        if not history:
            return result
        last_assistant = next((m for m in reversed(history) if m.get("role") == "assistant"), None)
        if not last_assistant:
            return result

        follow_up_patterns = [r"only", r"also", r"those", r"them", r"filter", r"show only", r"what about"]
        if any(re.search(p, query.lower()) for p in follow_up_patterns):
            result.confidence = min(result.confidence + 5, 99.0)
            prev_type = last_assistant.get("chat_type")
            if prev_type and result.chat_type == ChatType.KNOWLEDGE:
                try:
                    result.chat_type = ChatType(prev_type)
                except ValueError:
                    pass
        return result
