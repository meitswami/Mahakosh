from typing import Type

import structlog

from backend.workflows.base import BaseWorkflow, WorkflowDefinition, WorkflowStepDefinition
from backend.workflows.workflow_events import NodeType, WorkflowType

logger = structlog.get_logger(__name__)

AGENT_NODE_MAP: dict[str, NodeType] = {
    "ocr": NodeType.AGENT,
    "validation": NodeType.VALIDATION,
    "vendor": NodeType.AGENT,
    "item": NodeType.AGENT,
    "gst": NodeType.VALIDATION,
    "hsn": NodeType.AGENT,
    "accounting": NodeType.AGENT,
    "approval": NodeType.APPROVAL,
    "audit": NodeType.TASK,
    "search": NodeType.AGENT,
    "reporting": NodeType.TASK,
    "workflow": NodeType.TASK,
    "tally": NodeType.AGENT,
}


class WorkflowRegistry:
    """Central registry for workflow templates and definitions."""

    def __init__(self) -> None:
        self._workflows: dict[str, Type[BaseWorkflow]] = {}
        self._instances: dict[str, BaseWorkflow] = {}

    def register(self, workflow_class: Type[BaseWorkflow]) -> Type[BaseWorkflow]:
        self._workflows[workflow_class.definition.workflow_type] = workflow_class
        logger.info("workflow_registered", type=workflow_class.definition.workflow_type)
        return workflow_class

    def get(self, workflow_type: str) -> BaseWorkflow:
        if workflow_type not in self._instances:
            if workflow_type not in self._workflows:
                raise KeyError(f"Workflow '{workflow_type}' not registered")
            self._instances[workflow_type] = self._workflows[workflow_type]()
        return self._instances[workflow_type]

    def list_templates(self) -> list[dict]:
        return [
            {
                "name": cls.definition.name,
                "workflow_type": cls.definition.workflow_type,
                "description": cls.definition.description,
                "step_count": len(cls.definition.steps),
                "agents": [s.agent_name for s in cls.definition.steps],
            }
            for cls in self._workflows.values()
        ]

    def get_step_node_type(self, agent_name: str) -> str:
        return AGENT_NODE_MAP.get(agent_name, NodeType.TASK).value

    def build_steps_definition(self, definition: WorkflowDefinition) -> list[dict]:
        steps = []
        steps.append({"name": "start", "node_type": NodeType.START.value, "order": 0})
        for s in definition.steps:
            steps.append({
                "name": s.name,
                "agent_name": s.agent_name,
                "node_type": self.get_step_node_type(s.agent_name),
                "order": s.order,
                "retry_limit": s.retry_limit,
                "timeout_seconds": s.timeout_seconds,
            })
        steps.append({"name": "end", "node_type": NodeType.END.value, "order": len(definition.steps) + 1})
        return steps


workflow_registry = WorkflowRegistry()
