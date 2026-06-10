# MAHAKOSH

**ज्ञान से निर्णय तक** — AI-Native Business Intelligence Operating System

Mahakosh combines document intelligence, OCR, knowledge bases, AI agent swarms, accounting intelligence, workflow automation, MCP connectors, and Tally integration for Indian businesses, CA firms, enterprises, and government organizations.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────────────────────┐
│   Next.js   │────▶│    Nginx    │────▶│         FastAPI Backend          │
│  Frontend   │     │   Reverse   │     │  Auth · Agents · Workflows · API │
└─────────────┘     │    Proxy    │     └──────────┬───────────────────────┘
                    └─────────────┘                │
         ┌─────────────────────────────────────────┼─────────────────────────┐
         │                                         │                         │
    ┌────▼────┐  ┌───────┐  ┌────────┐  ┌────────▼──┐  ┌─────────┐  ┌──────┐
    │PostgreSQL│  │ Redis │  │ Qdrant │  │   MinIO   │  │Temporal │  │Ollama│
    └─────────┘  └───────┘  └────────┘  └───────────┘  └─────────┘  └──────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, TypeScript, TailwindCSS, ShadCN UI, Zustand, React Query |
| Backend | FastAPI, Python 3.12 |
| Database | PostgreSQL |
| Vector DB | Qdrant |
| Object Storage | MinIO |
| Cache | Redis |
| Workflow | Temporal |
| AI Runtime | Ollama |
| Containers | Docker, Docker Compose |

## Quick Start

```bash
# Copy environment configuration
cp .env.example .env

# Start all services
docker compose up -d

# Access points
# Frontend:     http://localhost:3000
# API:          http://localhost:8000/api/v1
# API Docs:     http://localhost:8000/docs
# Temporal UI:  http://localhost:8080
# MinIO Console: http://localhost:9001
```

## Project Structure

```
mahakosh/
├── apps/                  # Future micro-app modules
├── backend/               # FastAPI application
│   ├── api/               # Versioned API routes
│   ├── agents/            # AI agent swarm framework
│   ├── connectors/        # MCP connector framework
│   ├── core/              # Config, security, database
│   ├── models/            # SQLAlchemy ORM models
│   ├── workflows/         # Temporal workflow framework
│   └── ...
├── frontend/              # Next.js 15 application
├── infrastructure/        # Docker, nginx, scripts
├── docs/                  # Documentation
├── storage/               # Local file storage
├── deployments/           # K8s manifests (future)
└── tools/                 # Development utilities
```

## API Versioning

All endpoints are under `/api/v1`:

- `auth` — Authentication & authorization
- `documents` — Document management
- `ocr` — OCR processing
- `knowledge` — Knowledge base
- `chat` — AI chat interface
- `accounting` — Accounting operations
- `gst` — GST validation & compliance
- `workflows` — Workflow management
- `reports` — Reporting
- `audit` — Audit logs
- `agents` — Agent execution
- `admin` — Administration

## Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn backend.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## License

Proprietary — All rights reserved.
