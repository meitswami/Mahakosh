# Mahakosh Workflow Engine

**ज्ञान से निर्णय तक** — Every step from input to output is visible, auditable, and replayable.

## Architecture

```
Input → Workflow → Agents → Validation → Approval → Output
         ↑ visible at every layer
```

### Backend Modules (`backend/workflows/`)

| Module | Purpose |
|--------|---------|
| `workflow_engine.py` | Production orchestrator with audit + metrics |
| `workflow_runner.py` | Step execution with retry → fallback → manual review |
| `workflow_tracker.py` | Event emission, Redis pub/sub, execution logs |
| `workflow_registry.py` | Template registry and node type mapping |
| `workflow_visualizer.py` | Node-based graph builder + replay |
| `timeline_builder.py` | Execution timeline from steps/events/logs |
| `approval_manager.py` | Approval queue integration |
| `execution_monitor.py` | Live workflows, agent activity, analytics |
| `workflow_state_manager.py` | State transitions and duration calc |
| `workflow_events.py` | Event types, node types, workflow types |

### Temporal Integration (`backend/temporal/`)

- `client.py` — Lazy Temporal client with graceful fallback
- `workflows.py` — `MahakoshWorkflow` with retry/cancel signals
- `activities.py` — Durable activity wrapping the in-process engine
- `worker.py` — Worker entry point (`python -m backend.temporal.worker`)

## Workflow Templates

| Type | Steps | Agents |
|------|-------|--------|
| `document_processing` | 9 | ocr → validation → vendor → item → gst → hsn → accounting → approval → audit |
| `gst_validation` | 3 | gst → hsn → audit |
| `approval_flow` | 3 | validation → approval → audit |
| `report_generation` | 3 | search → reporting → audit |
| `vendor_onboarding` | 4 | vendor → gst → approval → audit |
| `item_creation` | 4 | item → hsn → validation → audit |
| `tally_export` | 3 | accounting → tally → audit |

## Workflow States

`pending` → `queued` → `running` → `waiting` | `paused` → `completed` | `failed` | `cancelled`

Failed workflows can transition back to `queued` via retry.

## Retry Framework

```
Step Failure → Retry (up to limit) → Fallback Agent → Manual Review (approval)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/workflows` | List workflows (paginated) |
| GET | `/api/v1/workflows/templates` | List available templates |
| GET | `/api/v1/workflows/{id}` | Workflow detail + steps |
| GET | `/api/v1/workflows/{id}/graph` | Node graph (`?replay=true` for replay) |
| GET | `/api/v1/workflows/{id}/timeline` | Execution timeline |
| GET | `/api/v1/workflows/{id}/logs` | Execution logs |
| GET | `/api/v1/workflows/live` | Active workflows |
| GET | `/api/v1/workflows/analytics` | Workflow metrics |
| GET | `/api/v1/workflows/agents/activity` | Agent health panel |
| GET | `/api/v1/workflows/approvals/pending` | Pending approvals |
| GET | `/api/v1/workflows/approvals/history` | Approval history |
| POST | `/api/v1/workflows` | Create workflow |
| POST | `/api/v1/workflows/{id}/execute` | Execute workflow |
| POST | `/api/v1/workflows/retry` | Retry failed/waiting workflow |
| POST | `/api/v1/workflows/cancel` | Cancel workflow |
| WS | `/api/v1/workflows/live/stream` | Real-time events (Redis pub/sub) |
| GET | `/api/v1/workflows/live/events` | SSE stream |

## Database Tables

- `workflow_templates` — Template definitions
- `workflow_instances` — `workflows` table
- `workflow_steps` — Per-step tracking
- `workflow_events` — Real-time event log
- `workflow_logs` — Input/output/reasoning per step
- `workflow_approvals` — Approval links
- `workflow_metrics` — Daily aggregated metrics

Migration: `006_workflow_monitoring_tables.py`

## Frontend

- **Workflow Center** (`/workflows`) — Templates, live monitor, analytics, agent activity, approvals
- **Workflow Detail** (`/workflows/[id]`) — Graph, timeline, logs, replay mode

## Real-Time Updates

Events are published to Redis channel `mahakosh:workflows:live:{tenant_id}`. Connect via WebSocket or SSE for live dashboard updates.

## Security

- RBAC: Accountants create/execute; Managers cancel
- Tenant isolation on all queries
- Audit logging on create, execute, retry, cancel, complete, fail

## Workflow Replay

Completed or failed workflows support replay mode on the detail page. Each node shows agent decisions and reasoning summaries from execution logs.

## Transparency Framework

Every workflow produces a **Transparency Manifest** — users can answer all six questions without reading logs:

| Question | Manifest Field |
|----------|----------------|
| What happened? | `what_happened` / `questions.what_happened` |
| Why did it happen? | `why_it_happened` / `questions.why_did_it_happen` |
| Which agent executed it? | `agents_executed` |
| Which documents were used? | `documents_used` |
| Which validations were performed? | `validations_performed` |
| Who approved it? | `approvals` |

**API:** `GET /api/v1/workflows/{id}/transparency`  
Also included inline on `GET /api/v1/workflows/{id}`.

Manifests are persisted on workflow completion/failure/waiting in `workflows.transparency_manifest` (migration 007).
