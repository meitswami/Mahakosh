from backend.chat.citation_engine import ChatCitationEngine
from backend.chat.types import ChatPipelineResult, ChatType, IntentResult


class ResponseGenerator:
    """Format final chat responses with structured data and citations."""

    def __init__(self):
        self.citation_engine = ChatCitationEngine()

    def generate(
        self,
        answer: str,
        pipeline: ChatPipelineResult,
        intent: IntentResult,
        structured_data: dict,
        citations: list[dict],
    ) -> ChatPipelineResult:
        pipeline.answer = answer
        pipeline.structured_data = structured_data
        pipeline.citations = citations
        pipeline.confidence = structured_data.get("confidence", intent.confidence)

        if structured_data and intent.chat_type in (ChatType.ACCOUNTING, ChatType.REPORTING):
            summary = self.citation_engine.build_summary_block(structured_data, citations)
            if summary and summary not in answer:
                pipeline.answer = f"{answer}\n\n---\n{summary}"

        return pipeline

    def fallback_answer(self, knowledge_context: str, query: str) -> str:
        if knowledge_context:
            return (
                f"Based on retrieved knowledge for \"{query}\":\n\n"
                f"{knowledge_context[:3500]}"
            )
        return (
            "I couldn't find relevant data in your knowledge base for this query. "
            "Try indexing documents or rephrasing your question."
        )
