# Mahakosh Agent Swarm

Production multi-agent architecture for task decomposition, coordination, parallel execution, consensus validation, and human-in-the-loop approvals.

## Architecture Rule

Agents **never** read files, OCR outputs, or databases directly. All data flows through:

- `KnowledgeTool` → Retrieval Engine
- `WorkflowTool` → Workflow Engine
- `ApprovalTool` → Approval Queue

## Folder Structure

```
backend/agents/
├── base/           # BaseAgent, types, confidence framework
├── orchestrator/   # Master orchestrator, execution engine, decomposer
├── specialists/    # Domain agents (plugin-registered)
├── communication/  # Redis Pub/Sub event bus
├── memory/         # Task, workflow, knowledge memory
├── consensus/      # Cross-agent validation engine
├── registry/       # Dynamic agent registry
└── tools/          # Knowledge, Workflow, Approval, Model Router
```

## Agents (14)

| Agent | Name | Purpose |
|-------|------|---------|
| Master Orchestrator | `master_orchestrator` | Task decomposition, coordination |
| OCR | `ocr` | Workflow trigger + knowledge lookup |
| Validation | `validation` | Field validation via knowledge |
| Vendor | `vendor` | Vendor matching |
| Item | `item` | Line item resolution |
| GST | `gst` | Tax computation |
| HSN | `hsn` | HSN classification |
| Accounting | `accounting` | Voucher drafting (approval required) |
| Search | `search` | Hybrid knowledge search |
| Reporting | `reporting` | BI report generation |
| Workflow | `workflow` | Workflow lifecycle |
| Audit | `audit` | Compliance verification |
| Approval | `approval` | Human-in-the-loop queue |
| Tally | `tally` | Tally export (write requires approval) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/agents` | List registered agents |
| GET | `/api/v1/agents/status` | Swarm status + health |
| GET | `/api/v1/agents/health` | Per-agent health metrics |
| GET | `/api/v1/agents/executions` | Execution history |
| GET | `/api/v1/agents/events` | Event bus history |
| GET | `/api/v1/agents/approvals/pending` | Pending approvals |
| POST | `/api/v1/agents/orchestrate` | Run master orchestrator |
| POST | `/api/v1/agents/{name}/execute` | Execute single agent |

## Adding New Agents

1. Create `backend/agents/specialists/my_agent.py` inheriting `SpecialistAgent`
2. Add to `ALL_AGENTS` in `specialists/__init__.py`
3. Agent auto-registers via `agent_registry.register()`

No changes to existing agents required.

## Confidence Framework

Every agent returns: `result`, `confidence`, `reasoning`, `sources`, `execution_time`

| Score | Level |
|-------|-------|
| 95+ | High |
| 80-95 | Medium |
| <80 | Needs Review |

## Migration

```bash
cd backend && alembic upgrade head
```

Applies `004_agent_swarm_tables.py`.
