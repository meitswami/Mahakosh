# Mahakosh AI Chat & Reasoning Layer

Primary natural-language interface for documents, knowledge, accounting, workflows, agents, and reports.

## Pipeline

```
User → Chat Gateway → Intent Engine → Orchestrator/Agents
     → Knowledge Retrieval → Context Builder → Reasoning Engine
     → Response Generator (+ Citations) → User
```

## Transparency Rule

Unlike traditional chatbots, Mahakosh exposes its reasoning path on **every response**.

Each answer includes a `transparency` manifest:

| Field | Description |
|-------|-------------|
| `agents_participated` | Which agents ran (orchestrator, search, specialists) |
| `documents_consulted` | Source documents with chunk counts |
| `chunks_retrieved` | Knowledge chunk IDs, pages, excerpts, confidence |
| `confidence_score` | Overall confidence (high ≥95%, medium 80–95%, needs review <80%) |
| `sources` | Full citations with page numbers |
| `reasoning_path` | Step-by-step pipeline trace |

Users never have to blindly trust the AI.

## Chat Types

`general`, `knowledge`, `document`, `accounting`, `workflow`, `reporting`, `agent`

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat/query` | Send message, get full response |
| GET | `/api/v1/chat/history` | List conversation sessions |
| GET | `/api/v1/chat/session/{id}` | Get session with messages |
| DELETE | `/api/v1/chat/session/{id}` | Delete session |
| WS | `/api/v1/chat/stream?token=` | Streaming with reasoning steps |
| POST | `/api/v1/chat/saved-queries` | Save frequent query |
| GET | `/api/v1/chat/saved-queries` | List saved queries |

## Modules

| Module | Path |
|--------|------|
| Gateway | `backend/chat/chat_gateway.py` |
| Orchestrator | `backend/chat/chat_orchestrator.py` |
| Intent | `backend/chat/intent_engine.py` |
| Retrieval | `backend/chat/retrieval_service.py` |
| Context | `backend/chat/context_builder.py` |
| Reasoning | `backend/chat/reasoning_engine.py` |
| Memory | `backend/chat/memory_manager.py` |
| Conversations | `backend/chat/conversation_manager.py` |
| Citations | `backend/chat/citation_engine.py` |
| Response | `backend/chat/response_generator.py` |

## Database Tables

`chat_sessions`, `chat_messages`, `chat_context`, `chat_memory`, `saved_queries`

## Migration

```bash
cd backend && alembic upgrade head
```

Applies `005_chat_tables.py`.

## Future Channels

Architecture supports WhatsApp, Telegram, and Voice via the same `ChatGateway` entry point.
