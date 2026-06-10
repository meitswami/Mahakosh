from dataclasses import dataclass, field
from typing import Any


@dataclass
class SubTask:
    task_id: str
    agent_name: str
    input_data: dict[str, Any]
    depends_on: list[str] = field(default_factory=list)
    parallel_group: int = 0


@dataclass
class TaskPlan:
    task_type: str
    subtasks: list[SubTask]
    execution_mode: str = "sequential"
    description: str = ""


class TaskDecomposer:
    """Decompose high-level tasks into agent subtasks."""

    ROUTING: dict[str, dict[str, Any]] = {
        "document_processing": {
            "agents": ["ocr", "validation", "vendor", "item", "gst", "hsn", "accounting"],
            "mode": "sequential",
        },
        "batch_invoice_processing": {
            "agents": ["ocr", "validation", "gst", "accounting"],
            "mode": "batch",
        },
        "gst_validation": {
            "agents": ["gst", "validation"],
            "mode": "parallel",
            "parallel_groups": [[0, 1]],
        },
        "report_generation": {
            "agents": ["search", "reporting"],
            "mode": "sequential",
        },
        "approval_flow": {
            "agents": ["validation", "approval", "audit"],
            "mode": "sequential",
        },
        "tally_export": {
            "agents": ["accounting", "approval", "tally"],
            "mode": "sequential",
        },
        "general": {
            "agents": ["search"],
            "mode": "sequential",
        },
    }

    def decompose(self, task_type: str, payload: dict[str, Any]) -> TaskPlan:
        config = self.ROUTING.get(task_type, self.ROUTING["general"])
        agents = config["agents"]
        mode = config["mode"]
        batch_count = payload.get("batch_count", 1)

        subtasks: list[SubTask] = []
        if mode == "batch" and batch_count > 1:
            items = payload.get("items", [{}] * batch_count)
            for i, item in enumerate(items):
                for j, agent in enumerate(agents):
                    subtasks.append(SubTask(
                        task_id=f"batch-{i}-{agent}",
                        agent_name=agent,
                        input_data={**payload, **item, "batch_index": i},
                        parallel_group=i * len(agents) + j,
                    ))
        else:
            for i, agent in enumerate(agents):
                subtasks.append(SubTask(
                    task_id=f"{task_type}-{agent}-{i}",
                    agent_name=agent,
                    input_data=payload,
                    depends_on=[subtasks[-1].task_id] if subtasks and mode == "sequential" else [],
                    parallel_group=0 if mode == "sequential" else i,
                ))

        return TaskPlan(
            task_type=task_type,
            subtasks=subtasks,
            execution_mode=mode,
            description=f"Decomposed {task_type} into {len(subtasks)} subtasks",
        )


task_decomposer = TaskDecomposer()
