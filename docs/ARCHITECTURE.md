# Mahakosh Architecture

## System Overview

Mahakosh is a multi-tenant AI-native business intelligence platform designed for Indian enterprises, CA firms, and government organizations.

## Core Layers

### 1. Presentation Layer (Next.js 15)
- Server and client components
- Zustand for client state
- React Query for server state
- ShadCN UI component library

### 2. API Layer (FastAPI)
- Versioned REST API (`/api/v1`)
- JWT authentication with RBAC
- Tenant-scoped data isolation
- Structured logging with request tracing

### 3. Intelligence Layer (Agent Swarm)
- 13 specialized agents orchestrated by MasterOrchestratorAgent
- Pluggable agent registry
- Execution tracking in `agent_executions` table

### 4. Workflow Layer (Temporal)
- State machine: Pending → Queued → Running → Waiting → Completed/Failed/Cancelled
- Document processing pipeline as first workflow definition
- Step-level retry and error handling

### 5. Connector Layer (MCP)
- Base MCP connector framework
- Tally ERP integration connector
- Extensible connector registry

### 6. Data Layer
- PostgreSQL: transactional data (26 tables)
- Qdrant: vector embeddings for semantic search
- MinIO: document object storage
- Redis: caching and session management

## Multi-Tenancy

Every data table includes `tenant_id` with foreign key to `tenants`. API middleware extracts tenant context from JWT claims. All repository queries are tenant-scoped.

## Security Model

| Role | Level | Permissions |
|------|-------|-------------|
| Admin | 100 | Full access |
| Manager | 80 | Read, write, approve |
| Accountant | 60 | Read, write, accounting |
| Auditor | 40 | Read, audit |
| Viewer | 20 | Read only |
