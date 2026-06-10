from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class TaskRecord:
    task_id: str
    task_type: str
    status: str = "pending"
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    assigned_agents: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class TaskMemory:
    """Short-lived in-memory task store keyed by tenant."""

    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, TaskRecord]] = {}

    def _tenant_key(self, tenant_id: str) -> dict[str, TaskRecord]:
        return self._tasks.setdefault(tenant_id, {})

    def create(self, tenant_id: str, task_type: str, inputs: dict[str, Any]) -> TaskRecord:
        task = TaskRecord(task_id=str(uuid4()), task_type=task_type, inputs=inputs)
        self._tenant_key(tenant_id)[task.task_id] = task
        return task

    def get(self, tenant_id: str, task_id: str) -> TaskRecord | None:
        return self._tenant_key(tenant_id).get(task_id)

    def update(self, tenant_id: str, task_id: str, **kwargs: Any) -> TaskRecord | None:
        task = self.get(tenant_id, task_id)
        if not task:
            return None
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        task.updated_at = datetime.now(UTC).isoformat()
        return task

    def list_active(self, tenant_id: str) -> list[TaskRecord]:
        return [t for t in self._tenant_key(tenant_id).values() if t.status in ("pending", "running")]


task_memory = TaskMemory()
