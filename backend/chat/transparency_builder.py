from typing import Any

from backend.agents.base.types import confidence_level
from backend.chat.types import ChatPipelineResult, ReasoningStep


class TransparencyBuilder:
    """Build the Mahakosh transparency manifest — users never blindly trust AI."""

    def build(
        self,
        pipeline: ChatPipelineResult,
        retrieval: dict[str, Any] | None = None,
        agent_details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        citations = pipeline.citations or []
        agents = self._normalize_agents(pipeline.agents_used, retrieval, agent_details)
        documents = self._extract_documents(citations, retrieval)
        chunks = self._extract_chunks(citations, retrieval)
        sources = self._build_sources(citations)
        conf = self._resolve_confidence(pipeline, citations)
        level = confidence_level(conf)

        return {
            "agents_participated": agents,
            "documents_consulted": documents,
            "chunks_retrieved": chunks,
            "confidence_score": round(conf, 1),
            "confidence_level": level.value,
            "confidence_display": f"{round(conf, 1)}%",
            "sources": sources,
            "reasoning_path": [s.to_dict() for s in pipeline.reasoning_steps],
            "knowledge_query_id": str(pipeline.query_id) if pipeline.query_id else None,
            "model_used": pipeline.model_used,
            "processing_time_ms": pipeline.processing_time_ms,
            "summary": self._build_summary(agents, documents, chunks, conf),
        }

    def _normalize_agents(
        self,
        agents_used: list[str],
        retrieval: dict | None,
        agent_details: dict | None,
    ) -> list[dict[str, Any]]:
        agents: list[dict[str, Any]] = []
        seen: set[str] = set()

        if retrieval and retrieval.get("total_found", 0) >= 0:
            for name in ("search", "knowledge_retrieval"):
                if name not in seen:
                    agents.append({
                        "name": name,
                        "role": "knowledge_retrieval",
                        "description": "Hybrid search across knowledge base",
                    })
                    seen.add(name)

        for name in agents_used or []:
            if name in seen:
                continue
            detail = (agent_details or {}).get(name, {})
            agents.append({
                "name": name,
                "role": "specialist",
                "description": detail.get("reasoning", f"{name} agent executed"),
                "confidence": detail.get("confidence"),
                "success": detail.get("success", True),
            })
            seen.add(name)

        if "master_orchestrator" not in seen:
            agents.insert(0, {
                "name": "chat_orchestrator",
                "role": "orchestration",
                "description": "Intent detection, retrieval, and response coordination",
            })

        return agents

    def _extract_documents(
        self,
        citations: list[dict],
        retrieval: dict | None,
    ) -> list[dict[str, Any]]:
        docs: dict[str, dict] = {}
        for c in citations:
            doc_id = c.get("document_id", "")
            if not doc_id:
                continue
            if doc_id not in docs:
                docs[doc_id] = {
                    "document_id": doc_id,
                    "title": c.get("source_document", "Unknown"),
                    "document_type": c.get("document_type"),
                    "chunks_used": 0,
                }
            docs[doc_id]["chunks_used"] += 1

        if retrieval:
            for r in retrieval.get("results", []):
                doc_id = str(r.document_id) if hasattr(r, "document_id") else str(r.get("document_id", ""))
                if doc_id and doc_id not in docs:
                    title = r.document_title if hasattr(r, "document_title") else r.get("document_title", "Unknown")
                    docs[doc_id] = {
                        "document_id": doc_id,
                        "title": title,
                        "document_type": r.document_type if hasattr(r, "document_type") else r.get("document_type"),
                        "chunks_used": 1,
                    }

        return list(docs.values())

    def _extract_chunks(
        self,
        citations: list[dict],
        retrieval: dict | None,
    ) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        for c in citations:
            chunks.append({
                "chunk_id": c.get("chunk_id", ""),
                "document_id": c.get("document_id", ""),
                "document_title": c.get("source_document", ""),
                "page_number": c.get("page_number"),
                "confidence": c.get("confidence", 0),
                "excerpt": c.get("excerpt", "")[:200],
                "rank": c.get("rank", 0),
            })

        if not chunks and retrieval:
            for i, r in enumerate(retrieval.get("results", [])):
                chunk_id = str(r.chunk_id) if hasattr(r, "chunk_id") else str(r.get("chunk_id", ""))
                chunks.append({
                    "chunk_id": chunk_id,
                    "document_id": str(r.document_id) if hasattr(r, "document_id") else str(r.get("document_id", "")),
                    "document_title": r.document_title if hasattr(r, "document_title") else r.get("document_title", ""),
                    "page_number": r.page_number if hasattr(r, "page_number") else r.get("page_number"),
                    "confidence": round((r.score if hasattr(r, "score") else r.get("score", 0)) * 100, 1),
                    "excerpt": (r.content if hasattr(r, "content") else r.get("content", ""))[:200],
                    "rank": i + 1,
                })
        return chunks

    def _build_sources(self, citations: list[dict]) -> list[dict[str, Any]]:
        return [
            {
                "source_document": c.get("source_document", ""),
                "document_id": c.get("document_id", ""),
                "chunk_id": c.get("chunk_id", ""),
                "page_number": c.get("page_number"),
                "confidence": c.get("confidence", 0),
                "confidence_display": c.get("confidence_display", f"{c.get('confidence', 0)}%"),
                "citation_text": c.get("citation_text", ""),
            }
            for c in citations
        ]

    def _resolve_confidence(self, pipeline: ChatPipelineResult, citations: list[dict]) -> float:
        if pipeline.structured_data.get("confidence"):
            return float(pipeline.structured_data["confidence"])
        if citations:
            confs = [c.get("confidence", 0) for c in citations if c.get("confidence")]
            if confs:
                return sum(confs) / len(confs)
        return pipeline.confidence

    def _build_summary(
        self,
        agents: list[dict],
        documents: list[dict],
        chunks: list[dict],
        confidence: float,
    ) -> str:
        agent_names = ", ".join(a["name"] for a in agents[:5])
        return (
            f"{len(agents)} agent(s) participated · "
            f"{len(documents)} document(s) consulted · "
            f"{len(chunks)} chunk(s) retrieved · "
            f"{round(confidence, 1)}% confidence"
        )


transparency_builder = TransparencyBuilder()
