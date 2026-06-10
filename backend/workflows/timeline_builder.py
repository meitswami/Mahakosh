from typing import Any

from backend.models.workflow import Workflow, WorkflowStep
from backend.models.workflow_monitoring import WorkflowEventRecord, WorkflowLog


class TimelineBuilder:
    """Build execution timeline from steps, events, and logs."""

    def build(
        self,
        workflow: Workflow,
        steps: list[WorkflowStep],
        events: list[WorkflowEventRecord] | None = None,
        logs: list[WorkflowLog] | None = None,
    ) -> list[dict[str, Any]]:
        timeline: list[dict[str, Any]] = []

        if workflow.started_at:
            timeline.append({
                "type": "workflow_start",
                "label": "Workflow Started",
                "status": "completed",
                "timestamp": workflow.started_at.isoformat(),
                "agent_name": None,
                "duration_ms": None,
                "error": None,
            })

        for step in sorted(steps, key=lambda s: s.step_order):
            duration = None
            if step.started_at and step.completed_at:
                duration = int((step.completed_at - step.started_at).total_seconds() * 1000)

            step_logs = [l for l in (logs or []) if l.step_id == step.id]
            reasoning = step_logs[0].reasoning_summary if step_logs else None

            timeline.append({
                "type": "step",
                "step_id": str(step.id),
                "label": step.step_name.replace("_", " ").title(),
                "status": step.status,
                "agent_name": step.agent_name,
                "node_type": step.node_type,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "timestamp": step.started_at.isoformat() if step.started_at else None,
                "duration_ms": duration,
                "error": step.error_message,
                "retry_count": step.retry_count,
                "reasoning_summary": reasoning,
                "confidence": step_logs[0].confidence if step_logs else None,
            })

        if events:
            for ev in events:
                if ev.event_type in ("approval_required", "approval_resolved"):
                    timeline.append({
                        "type": "approval",
                        "label": ev.event_type.replace("_", " ").title(),
                        "status": ev.payload.get("status", "pending"),
                        "timestamp": ev.created_at.isoformat(),
                        "agent_name": ev.agent_name,
                        "payload": ev.payload,
                    })

        if workflow.completed_at:
            timeline.append({
                "type": "workflow_end",
                "label": f"Workflow {workflow.status.title()}",
                "status": workflow.status,
                "timestamp": workflow.completed_at.isoformat(),
                "duration_ms": (
                    int((workflow.completed_at - workflow.started_at).total_seconds() * 1000)
                    if workflow.started_at else None
                ),
                "error": workflow.error_message,
            })

        timeline.sort(key=lambda t: t.get("timestamp") or "")
        return timeline
