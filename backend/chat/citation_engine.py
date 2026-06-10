from typing import Any

from backend.services.knowledge.types import RetrievalResult


class ChatCitationEngine:
    """Format citations for chat responses with source, page, chunk, confidence."""

    def from_retrieval_results(self, results: list[RetrievalResult]) -> list[dict[str, Any]]:
        citations = []
        for i, r in enumerate(results):
            conf = round(r.score * 100, 1)
            citations.append({
                "source_document": r.source_name or r.document_title,
                "document_id": str(r.document_id),
                "chunk_id": str(r.chunk_id),
                "page_number": r.page_number,
                "confidence": conf,
                "confidence_display": f"{conf}%",
                "rank": i + 1,
                "document_type": r.document_type,
                "excerpt": r.content[:250] + ("..." if len(r.content) > 250 else ""),
                "citation_text": self._format(r, conf),
            })
        return citations

    def from_dicts(self, citations: list[dict]) -> list[dict[str, Any]]:
        return [
            {
                "source_document": c.get("source_document", c.get("source_name", "Unknown")),
                "document_id": c.get("document_id", ""),
                "chunk_id": c.get("chunk_id", ""),
                "page_number": c.get("page_number"),
                "confidence": c.get("confidence", 0),
                "confidence_display": c.get("confidence_display", f"{c.get('confidence', 0)}%"),
                "rank": c.get("rank", i + 1),
                "excerpt": c.get("excerpt", ""),
                "citation_text": c.get("citation_text", ""),
            }
            for i, c in enumerate(citations)
        ]

    def _format(self, result: RetrievalResult, confidence: float) -> str:
        page = f"Page {result.page_number}" if result.page_number else "Page N/A"
        return (
            f"Source: {result.source_name or result.document_title}\n"
            f"{page}\n"
            f"Confidence: {confidence}%"
        )

    def build_summary_block(self, structured: dict[str, Any], citations: list[dict]) -> str:
        lines = []
        for key, val in structured.items():
            if val is not None and key not in ("raw", "metadata"):
                label = key.replace("_", " ").title()
                if isinstance(val, float):
                    lines.append(f"{label}: ₹{val:,.2f}" if "amount" in key or "purchase" in key else f"{label}: {val}")
                else:
                    lines.append(f"{label}: {val}")
        if citations:
            top = citations[0]
            lines.append(f"\nConfidence: {top.get('confidence_display', 'N/A')}")
            lines.append(f"Sources: {top.get('source_document', 'N/A')}")
            if top.get("page_number"):
                lines.append(f"Page {top['page_number']}")
        return "\n".join(lines)
