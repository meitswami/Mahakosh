from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class WorkflowMemoryRecord:
    workflow_id: str
    context: dict[str, Any] = field(default_factory=dict)
    execution_history: list[dict[str, Any]] = field(default_factory=list)
    agent_decisions: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class WorkflowMemory:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, WorkflowMemoryRecord]] = {}

    def get_or_create(self, tenant_id: str, workflow_id: str) -> WorkflowMemoryRecord:
        tenant = self._store.setdefault(tenant_id, {})
        if workflow_id not in tenant:
            tenant[workflow_id] = WorkflowMemoryRecord(workflow_id=workflow_id)
        return tenant[workflow_id]

    def record_step(
        self,
        tenant_id: str,
        workflow_id: str,
        agent_name: str,
        decision: dict[str, Any],
        output: dict[str, Any],
    ) -> None:
        record = self.get_or_create(tenant_id, workflow_id)
        entry = {
            "agent": agent_name,
            "decision": decision,
            "output_summary": {k: output.get(k) for k in list(output.keys())[:10]},
            "at": datetime.now(UTC).isoformat(),
        }
        record.execution_history.append(entry)
        record.agent_decisions.append(decision)
        record.updated_at = datetime.now(UTC).isoformat()

    def get(self, tenant_id: str, workflow_id: str) -> WorkflowMemoryRecord | None:
        return self._store.get(tenant_id, {}).get(workflow_id)


workflow_memory = WorkflowMemory()
