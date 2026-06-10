# Mahakosh Knowledge Base & Retrieval Engine

Central intelligence layer for document ingestion, embedding, hybrid search, reranking, citations, and knowledge graph foundations.

## Architecture

```
Document / OCR / Upload
        ↓
Knowledge Ingestion → Chunking → Embedding → PostgreSQL + Qdrant
        ↓
Retrieval Engine (keyword + vector + metadata + hybrid RRF)
        ↓
Reranker (bge-reranker-large) → Citation Engine → LLM / Agents / Chat
```

## Modules

| Module | Path | Purpose |
|--------|------|---------|
| Ingestion | `backend/services/knowledge/knowledge_ingestion.py` | PDF, DOCX, TXT, CSV, Excel, OCR, Tally |
| Chunker | `backend/services/knowledge/knowledge_chunker.py` | Semantic, recursive, table-aware |
| Embeddings | `backend/services/knowledge/embedding_service.py` | BGE-large-en-v1.5 |
| Qdrant | `backend/services/knowledge/qdrant_service.py` | Tenant-scoped vector collections |
| Indexer | `backend/services/knowledge/knowledge_indexer.py` | Chunk → embed → store |
| Retrieval | `backend/services/knowledge/retrieval_engine.py` | Hybrid search + LLM context |
| Reranker | `backend/services/knowledge/reranker.py` | bge-reranker-large |
| Citations | `backend/services/knowledge/citation_engine.py` | Source, page, confidence |
| Graph | `backend/services/knowledge/knowledge_graph_builder.py` | Neo4j-ready relationships |
| Orchestrator | `backend/services/knowledge/knowledge_orchestrator.py` | End-to-end indexing |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/knowledge/index` | Index text or OCR job |
| POST | `/api/v1/knowledge/index/upload` | Upload and index file |
| POST | `/api/v1/knowledge/search` | Hybrid/keyword/vector search |
| POST | `/api/v1/knowledge/hybrid-search` | Hybrid search shortcut |
| POST | `/api/v1/knowledge/semantic-search` | Vector search shortcut |
| POST | `/api/v1/knowledge/context` | LLM-ready context bundle |
| GET | `/api/v1/knowledge/document/{id}` | Document detail |
| GET | `/api/v1/knowledge/chunk/{id}` | Chunk detail |
| GET | `/api/v1/knowledge/collections` | List collections |
| GET | `/api/v1/knowledge/overview` | Dashboard stats |
| GET | `/api/v1/knowledge/graph/{id}` | Knowledge graph for document |

## Qdrant Collections (per tenant)

- `documents`, `invoices`, `vendors`, `customers`, `knowledge`, `chat_memory`, `workflow_memory`

Naming: `{QDRANT_COLLECTION_PREFIX}_{tenant_id}_{type}`

## Database Tables

`knowledge_documents`, `knowledge_chunks`, `knowledge_embeddings`, `knowledge_relationships`, `knowledge_collections`, `knowledge_tags`, `knowledge_sources`, `knowledge_citations`, `knowledge_queries`, `knowledge_feedback`

## Agent & Chat Integration

- **Search Agent** (`search`): calls `RetrievalEngine.search()`
- **Chat** (`/api/v1/chat`): retrieves context via `get_context_for_llm()`, then Ollama completion
- **OCR**: auto-indexes on pipeline completion via `KnowledgeOrchestrator.index_from_ocr()`

## Configuration

See `.env.example` for embedding, reranker, chunk size, and Qdrant settings.

## Migration

```bash
cd backend && alembic upgrade head
```

Applies `003_knowledge_tables.py`.
