from uuid import UUID

from backend.services.knowledge.types import RetrievalResult


class CitationEngine:
    """Builds traceable citations for every retrieval result."""

    def build_citation(
        self,
        result: RetrievalResult,
        rank: int = 0,
    ) -> dict:
        confidence_pct = round(result.score * 100, 1)
        return {
            "source_document": result.source_name or result.document_title,
            "document_id": str(result.document_id),
            "chunk_id": str(result.chunk_id),
            "page_number": result.page_number,
            "confidence": confidence_pct,
            "confidence_display": f"{confidence_pct}%",
            "rank": rank,
            "document_type": result.document_type,
            "excerpt": result.content[:300] + ("..." if len(result.content) > 300 else ""),
            "citation_text": self.format_citation(result, confidence_pct),
        }

    def build_citations(self, results: list[RetrievalResult]) -> list[dict]:
        return [self.build_citation(r, rank=i + 1) for i, r in enumerate(results)]

    def format_citation(self, result: RetrievalResult, confidence: float) -> str:
        page_str = f"Page: {result.page_number}" if result.page_number else "Page: N/A"
        return (
            f"Source: {result.source_name or result.document_title}\n"
            f"{page_str}\n"
            f"Confidence: {confidence}%"
        )

    def format_inline(self, result: RetrievalResult) -> str:
        conf = round(result.score * 100)
        page = f", p.{result.page_number}" if result.page_number else ""
        return f"[{result.source_name or result.document_title}{page}, {conf}%]"
