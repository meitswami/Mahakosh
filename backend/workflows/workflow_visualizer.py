from typing import Any
from uuid import UUID

from backend.models.workflow import Workflow, WorkflowStep
from backend.workflows.workflow_events import NodeType
from backend.workflows.workflow_registry import workflow_registry


class WorkflowVisualizer:
    """Build node-based workflow graphs for UI rendering."""

    def build_graph(
        self,
        workflow: Workflow,
        steps: list[WorkflowStep],
        template_steps: list[dict] | None = None,
    ) -> dict[str, Any]:
        nodes: list[dict] = []
        edges: list[dict] = []

        nodes.append({
            "id": "start",
            "type": NodeType.START.value,
            "label": "Start",
            "status": "completed" if workflow.started_at else "pending",
            "agent_name": None,
        })

        step_map = {s.step_name: s for s in steps}
        ordered = sorted(steps, key=lambda s: s.step_order)

        for i, step in enumerate(ordered):
            node_id = step.step_name
            nodes.append({
                "id": node_id,
                "type": step.node_type or workflow_registry.get_step_node_type(step.agent_name or ""),
                "label": step.step_name.replace("_", " ").title(),
                "status": step.status,
                "agent_name": step.agent_name,
                "step_order": step.step_order,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "error_message": step.error_message,
                "retry_count": step.retry_count,
            })
            prev_id = ordered[i - 1].step_name if i > 0 else "start"
            edges.append({"from": prev_id, "to": node_id, "type": "sequential"})

        end_status = "completed" if workflow.status == "completed" else (
            "failed" if workflow.status == "failed" else "pending"
        )
        nodes.append({
            "id": "end",
            "type": NodeType.END.value,
            "label": "End",
            "status": end_status,
            "agent_name": None,
        })
        if ordered:
            edges.append({"from": ordered[-1].step_name, "to": "end", "type": "sequential"})
        elif workflow.started_at:
            edges.append({"from": "start", "to": "end", "type": "sequential"})

        return {
            "workflow_id": str(workflow.id),
            "workflow_name": workflow.name,
            "workflow_type": workflow.workflow_type,
            "status": workflow.status,
            "nodes": nodes,
            "edges": edges,
            "assigned_agents": workflow.assigned_agents or [s.agent_name for s in ordered if s.agent_name],
        }

    def build_replay_graph(
        self,
        workflow: Workflow,
        steps: list[WorkflowStep],
        logs: list[dict],
    ) -> dict[str, Any]:
        graph = self.build_graph(workflow, steps)
        for node in graph["nodes"]:
            step_logs = [l for l in logs if l.get("step_name") == node["id"] or l.get("agent_name") == node.get("agent_name")]
            node["replay"] = {
                "logs": step_logs[:5],
                "decisions": [l.get("reasoning_summary") for l in step_logs if l.get("reasoning_summary")],
            }
        return graph
