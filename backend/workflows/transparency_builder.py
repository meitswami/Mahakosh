"""Mahakosh Workflow Transparency Framework — every workflow is explainable."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base.types import confidence_level
from backend.agents.registry import agent_registry
from backend.models.approval import ApprovalQueue
from backend.models.user import User
from backend.models.workflow import Workflow, WorkflowStep
from backend.models.workflow_monitoring import WorkflowEventRecord, WorkflowLog
from backend.workflows.approval_manager import ApprovalManager
from backend.workflows.workflow_registry import AGENT_NODE_MAP
from backend.workflows.workflow_events import NodeType

VALIDATION_AGENTS = frozenset({"validation", "gst", "hsn"})
VALIDATION_NODE_TYPES = frozenset({"validation"})

AGENT_PURPOSE: dict[str, str] = {
    "ocr": "Extract text and structured fields from uploaded documents",
    "validation": "Cross-validate extracted data against business rules",
    "vendor": "Match or identify vendor from knowledge base",
    "item": "Match line items and inventory records",
    "gst": "Validate GSTIN, tax rates, and compliance",
    "hsn": "Map HSN/SAC codes for tax classification",
    "accounting": "Generate accounting vouchers and ledger entries",
    "approval": "Route decisions through human approval gates",
    "audit": "Record audit trail for compliance",
    "search": "Retrieve relevant knowledge for context",
    "reporting": "Compile business reports from retrieved data",
    "tally": "Export vouchers to Tally-compatible format",
    "workflow": "Coordinate multi-step workflow execution",
}


class WorkflowTransparencyBuilder:
    """Build human-readable transparency manifests from workflow execution data."""

    def build(
        self,
        workflow: Workflow,
        steps: list[WorkflowStep],
        logs: list[WorkflowLog],
        events: list[WorkflowEventRecord],
        approvals: list[dict[str, Any]],
        creator_name: str | None = None,
    ) -> dict[str, Any]:
        log_by_step = {str(l.step_id): l for l in logs if l.step_id}
        agents_executed = self._build_agents_executed(steps, log_by_step)
        documents_used = self._extract_documents(workflow, steps, logs)
        validations = self._extract_validations(steps, log_by_step)
        approval_records = self._normalize_approvals(approvals)
        reasoning_path = self._build_reasoning_path(workflow, steps, logs, events)
        confidence = self._resolve_confidence(steps, logs)
        level = confidence_level(confidence)
        duration_ms = self._workflow_duration_ms(workflow)

        what = self._answer_what(workflow, steps)
        why = self._answer_why(workflow, creator_name)
        which_agents = self._answer_agents(agents_executed)
        which_docs = self._answer_documents(documents_used)
        which_validations = self._answer_validations(validations)
        who_approved = self._answer_approvals(approval_records)

        return {
            "workflow_id": str(workflow.id),
            "workflow_name": workflow.name,
            "workflow_type": workflow.workflow_type,
            "status": workflow.status,
            "what_happened": what,
            "why_it_happened": why,
            "summary": self._build_summary(workflow, agents_executed, documents_used, validations, confidence),
            "confidence_score": round(confidence, 1),
            "confidence_level": level.value,
            "confidence_display": f"{round(confidence, 1)}%",
            "processing_time_ms": duration_ms,
            "agents_executed": agents_executed,
            "documents_used": documents_used,
            "validations_performed": validations,
            "approvals": approval_records,
            "reasoning_path": reasoning_path,
            "questions": {
                "what_happened": what,
                "why_did_it_happen": why,
                "which_agent_executed": which_agents,
                "which_documents_were_used": which_docs,
                "which_validations_were_performed": which_validations,
                "who_approved_it": who_approved,
            },
        }

    def _build_agents_executed(
        self,
        steps: list[WorkflowStep],
        log_by_step: dict[str, WorkflowLog],
    ) -> list[dict[str, Any]]:
        agents: list[dict[str, Any]] = []
        for step in sorted(steps, key=lambda s: s.step_order):
            if step.step_name in ("start", "end") or not step.agent_name:
                continue
            log = log_by_step.get(str(step.id))
            duration = None
            if step.started_at and step.completed_at:
                duration = int((step.completed_at - step.started_at).total_seconds() * 1000)
            elif log and log.duration_ms:
                duration = log.duration_ms

            reasoning = (log.reasoning_summary if log else None) or step.output_data.get("reasoning", "")
            conf = log.confidence if log else step.output_data.get("confidence")

            agents.append({
                "name": step.agent_name,
                "step_name": step.step_name,
                "step_order": step.step_order,
                "node_type": step.node_type,
                "status": step.status,
                "purpose": self._agent_purpose(step.agent_name),
                "reasoning": reasoning or f"{step.agent_name} agent executed step '{step.step_name}'",
                "confidence": conf,
                "duration_ms": duration,
                "error": step.error_message or (log.error_message if log else None),
                "retry_count": step.retry_count,
            })
        return agents

    def _agent_purpose(self, agent_name: str) -> str:
        try:
            return agent_registry.get_class(agent_name).description
        except KeyError:
            return AGENT_PURPOSE.get(agent_name, f"{agent_name} specialist agent")

    def _extract_documents(
        self,
        workflow: Workflow,
        steps: list[WorkflowStep],
        logs: list[WorkflowLog],
    ) -> list[dict[str, Any]]:
        docs: dict[str, dict[str, Any]] = {}

        def add_doc(
            doc_id: str,
            title: str,
            *,
            document_type: str | None = None,
            step_name: str | None = None,
            agent_name: str | None = None,
            page_number: int | None = None,
        ) -> None:
            if not doc_id:
                return
            if doc_id not in docs:
                docs[doc_id] = {
                    "document_id": doc_id,
                    "title": title or f"Document {doc_id[:8]}",
                    "document_type": document_type,
                    "used_in_steps": [],
                    "agents": [],
                    "page_numbers": [],
                }
            if step_name and step_name not in docs[doc_id]["used_in_steps"]:
                docs[doc_id]["used_in_steps"].append(step_name)
            if agent_name and agent_name not in docs[doc_id]["agents"]:
                docs[doc_id]["agents"].append(agent_name)
            if page_number is not None and page_number not in docs[doc_id]["page_numbers"]:
                docs[doc_id]["page_numbers"].append(page_number)

        input_doc = workflow.input_data.get("document_id")
        if input_doc:
            add_doc(
                str(input_doc),
                workflow.input_data.get("document_title", workflow.input_data.get("name", "Input Document")),
                document_type=workflow.input_data.get("document_type"),
                step_name="input",
                agent_name=None,
            )

        if workflow.entity_type == "document" and workflow.entity_id:
            add_doc(str(workflow.entity_id), "Linked entity document", step_name="input")

        for step in steps:
            output = step.output_data or {}
            log_outputs = [l.output_data for l in logs if l.step_id == step.id]

            if output.get("document"):
                doc = output["document"]
                if isinstance(doc, dict):
                    add_doc(
                        str(doc.get("id", doc.get("document_id", ""))),
                        doc.get("title", doc.get("name", "Document")),
                        document_type=doc.get("document_type"),
                        step_name=step.step_name,
                        agent_name=step.agent_name,
                    )

            for src in output.get("sources", []) + output.get("citations", []):
                if isinstance(src, dict):
                    add_doc(
                        str(src.get("document_id", "")),
                        src.get("source_document", src.get("document_title", "Source")),
                        step_name=step.step_name,
                        agent_name=step.agent_name,
                        page_number=src.get("page_number"),
                    )

            for result in output.get("results", []):
                if isinstance(result, dict) and result.get("document_id"):
                    add_doc(
                        str(result["document_id"]),
                        result.get("document_title", "Knowledge document"),
                        step_name=step.step_name,
                        agent_name=step.agent_name,
                    )

            for log_out in log_outputs:
                for src in log_out.get("sources", []) + log_out.get("citations", []):
                    if isinstance(src, dict):
                        add_doc(
                            str(src.get("document_id", "")),
                            src.get("source_document", src.get("document_title", "Source")),
                            step_name=step.step_name,
                            agent_name=step.agent_name,
                            page_number=src.get("page_number"),
                        )

        return list(docs.values())

    def _extract_validations(
        self,
        steps: list[WorkflowStep],
        log_by_step: dict[str, WorkflowLog],
    ) -> list[dict[str, Any]]:
        validations: list[dict[str, Any]] = []
        for step in sorted(steps, key=lambda s: s.step_order):
            is_validation = (
                step.agent_name in VALIDATION_AGENTS
                or step.node_type in VALIDATION_NODE_TYPES
                or AGENT_NODE_MAP.get(step.agent_name or "") == NodeType.VALIDATION
            )
            output = step.output_data or {}
            has_validation_data = any(k in output for k in ("is_valid", "checks_passed", "issues", "issues_count"))

            if not is_validation and not has_validation_data:
                continue

            log = log_by_step.get(str(step.id))
            validations.append({
                "step_name": step.step_name,
                "agent_name": step.agent_name,
                "status": step.status,
                "is_valid": output.get("is_valid", step.status == "completed"),
                "checks_passed": output.get("checks_passed", []),
                "issues": output.get("issues", []),
                "reasoning": (log.reasoning_summary if log else None) or output.get("reasoning", ""),
                "confidence": log.confidence if log else output.get("confidence"),
            })
        return validations

    def _normalize_approvals(self, approvals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "approval_id": a.get("approval_id") or a.get("id"),
                "title": a.get("title", "Approval"),
                "status": a.get("status", "pending"),
                "action": a.get("action"),
                "requested_by": a.get("requested_by_name"),
                "reviewed_by": a.get("reviewed_by_name"),
                "reviewed_at": a.get("reviewed_at"),
                "review_notes": a.get("review_notes"),
            }
            for a in approvals
        ]

    def _build_reasoning_path(
        self,
        workflow: Workflow,
        steps: list[WorkflowStep],
        logs: list[WorkflowLog],
        events: list[WorkflowEventRecord],
    ) -> list[dict[str, Any]]:
        path: list[dict[str, Any]] = []

        if workflow.started_at:
            path.append({
                "step_type": "workflow_start",
                "label": "Workflow Started",
                "detail": f"{workflow.name} ({workflow.workflow_type}) began execution",
                "status": "completed",
            })

        log_by_step = {str(l.step_id): l for l in logs if l.step_id}
        for step in sorted(steps, key=lambda s: s.step_order):
            log = log_by_step.get(str(step.id))
            detail = (log.reasoning_summary if log else None) or step.output_data.get("reasoning", "")
            if not detail:
                detail = f"{step.agent_name or step.step_name} — {step.status}"
            path.append({
                "step_type": step.node_type or "step",
                "label": step.step_name.replace("_", " ").title(),
                "detail": detail,
                "status": step.status,
                "agent_name": step.agent_name,
            })

        for ev in events:
            if ev.event_type in ("approval_required", "approval_resolved", "step_failed", "workflow_failed"):
                path.append({
                    "step_type": ev.event_type,
                    "label": ev.event_type.replace("_", " ").title(),
                    "detail": ev.payload.get("reason") or ev.payload.get("error") or str(ev.payload),
                    "status": ev.payload.get("status", "info"),
                    "agent_name": ev.agent_name,
                })

        if workflow.completed_at:
            end_label = "Workflow Completed" if workflow.status == "completed" else f"Workflow {workflow.status.title()}"
            path.append({
                "step_type": "workflow_end",
                "label": end_label,
                "detail": workflow.error_message or f"Final status: {workflow.status}",
                "status": workflow.status,
            })

        return path

    def _resolve_confidence(self, steps: list[WorkflowStep], logs: list[WorkflowLog]) -> float:
        confs: list[float] = []
        for log in logs:
            if log.confidence is not None:
                confs.append(float(log.confidence))
        for step in steps:
            if step.output_data.get("confidence") is not None:
                confs.append(float(step.output_data["confidence"]))
        if confs:
            return sum(confs) / len(confs)
        completed = sum(1 for s in steps if s.status == "completed")
        total = len([s for s in steps if s.agent_name])
        if total == 0:
            return 0.0
        return round(completed / total * 100, 1)

    def _workflow_duration_ms(self, workflow: Workflow) -> int | None:
        if workflow.started_at and workflow.completed_at:
            return int((workflow.completed_at - workflow.started_at).total_seconds() * 1000)
        return None

    def _answer_what(self, workflow: Workflow, steps: list[WorkflowStep]) -> str:
        completed = sum(1 for s in steps if s.status == "completed")
        failed = [s.step_name for s in steps if s.status == "failed"]
        total = len([s for s in steps if s.agent_name])

        if workflow.status == "completed":
            return (
                f"The {workflow.name} workflow completed successfully. "
                f"{completed} of {total} agent steps executed without failure."
            )
        if workflow.status == "failed":
            return (
                f"The {workflow.name} workflow failed at step(s): {', '.join(failed) or 'unknown'}. "
                f"{completed} of {total} steps completed before failure."
            )
        if workflow.status == "waiting":
            return (
                f"The {workflow.name} workflow is paused awaiting manual review. "
                f"{completed} of {total} steps completed so far."
            )
        if workflow.status == "running":
            return f"The {workflow.name} workflow is currently running ({completed}/{total} steps done)."
        return f"The {workflow.name} workflow is {workflow.status}. {completed} of {total} steps completed."

    def _answer_why(self, workflow: Workflow, creator_name: str | None) -> str:
        trigger = workflow.input_data.get("trigger_reason") or workflow.input_data.get("reason")
        if trigger:
            return str(trigger)
        entity = workflow.entity_type or "business process"
        creator = creator_name or "a user"
        return (
            f"This {workflow.workflow_type.replace('_', ' ')} workflow was initiated by {creator} "
            f"to process {entity} data through Mahakosh's agent pipeline."
        )

    def _answer_agents(self, agents: list[dict[str, Any]]) -> str:
        if not agents:
            return "No agents have executed yet."
        executed = [a for a in agents if a["status"] in ("completed", "running", "failed", "waiting")]
        names = ", ".join(f"{a['name']} ({a['step_name']})" for a in executed)
        return f"Agents executed: {names}."

    def _answer_documents(self, documents: list[dict[str, Any]]) -> str:
        if not documents:
            return "No documents were referenced during this workflow."
        titles = ", ".join(d["title"] for d in documents[:5])
        suffix = f" and {len(documents) - 5} more" if len(documents) > 5 else ""
        return f"Documents used: {titles}{suffix}."

    def _answer_validations(self, validations: list[dict[str, Any]]) -> str:
        if not validations:
            return "No validation steps were performed."
        parts = []
        for v in validations:
            passed = len(v.get("checks_passed", []))
            issues = len(v.get("issues", []))
            valid = "passed" if v.get("is_valid") else "failed"
            parts.append(f"{v['step_name']} ({v['agent_name']}): {valid} — {passed} checks, {issues} issues")
        return "Validations: " + "; ".join(parts) + "."

    def _answer_approvals(self, approvals: list[dict[str, Any]]) -> str:
        if not approvals:
            return "No approval was required for this workflow."
        resolved = [a for a in approvals if a["status"] in ("approved", "rejected", "modified")]
        pending = [a for a in approvals if a["status"] == "pending"]
        if resolved:
            reviewers = ", ".join(
                f"{a['reviewed_by'] or 'Unknown'} ({a['status']})" for a in resolved if a.get("reviewed_by")
            )
            if reviewers:
                return f"Approved/reviewed by: {reviewers}."
        if pending:
            return f"{len(pending)} approval(s) pending human review."
        return "Approval records exist but no reviewer assigned yet."

    def _build_summary(
        self,
        workflow: Workflow,
        agents: list[dict[str, Any]],
        documents: list[dict[str, Any]],
        validations: list[dict[str, Any]],
        confidence: float,
    ) -> str:
        return (
            f"{workflow.status.title()} · "
            f"{len(agents)} agent(s) · "
            f"{len(documents)} document(s) · "
            f"{len(validations)} validation(s) · "
            f"{round(confidence, 1)}% confidence"
        )


workflow_transparency_builder = WorkflowTransparencyBuilder()


class WorkflowTransparencyService:
    """Load workflow data and produce transparency manifests."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.builder = workflow_transparency_builder

    async def build_for_workflow(self, workflow_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        workflow = await self._get_workflow(workflow_id, tenant_id)
        if (
            workflow.transparency_manifest
            and workflow.status in ("completed", "failed", "cancelled")
        ):
            return workflow.transparency_manifest

        return await self.build_and_optionally_persist(workflow, persist=workflow.status in (
            "completed", "failed", "cancelled", "waiting"
        ))

    async def build_and_persist(self, workflow: Workflow) -> dict[str, Any]:
        return await self.build_and_optionally_persist(workflow, persist=True)

    async def build_and_optionally_persist(
        self,
        workflow: Workflow,
        *,
        persist: bool,
    ) -> dict[str, Any]:
        steps, logs, events, approvals, creator_name = await self._load_context(workflow)
        manifest = self.builder.build(workflow, steps, logs, events, approvals, creator_name)
        if persist:
            workflow.transparency_manifest = manifest
            await self.db.flush()
        return manifest

    async def _load_context(self, workflow: Workflow) -> tuple[
        list[WorkflowStep],
        list[WorkflowLog],
        list[WorkflowEventRecord],
        list[dict[str, Any]],
        str | None,
    ]:
        steps_result = await self.db.execute(
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == workflow.id)
            .order_by(WorkflowStep.step_order)
        )
        steps = list(steps_result.scalars().all())

        logs_result = await self.db.execute(
            select(WorkflowLog)
            .where(WorkflowLog.workflow_id == workflow.id)
            .order_by(WorkflowLog.created_at)
        )
        logs = list(logs_result.scalars().all())

        events_result = await self.db.execute(
            select(WorkflowEventRecord)
            .where(WorkflowEventRecord.workflow_id == workflow.id)
            .order_by(WorkflowEventRecord.created_at)
        )
        events = list(events_result.scalars().all())

        approvals = await self._load_approvals(workflow)

        creator_name = None
        creator_result = await self.db.execute(
            select(User.full_name).where(User.id == workflow.created_by)
        )
        creator_name = creator_result.scalar_one_or_none()

        return steps, logs, events, approvals, creator_name

    async def _load_approvals(self, workflow: Workflow) -> list[dict[str, Any]]:
        manager = ApprovalManager(self.db)
        linked = await manager.get_workflow_approvals(workflow.tenant_id, workflow.id)

        entity_result = await self.db.execute(
            select(ApprovalQueue, User.full_name)
            .outerjoin(User, ApprovalQueue.reviewed_by == User.id)
            .where(
                ApprovalQueue.tenant_id == workflow.tenant_id,
                ApprovalQueue.entity_id == workflow.id,
            )
        )
        entity_approvals = [
            {
                "approval_id": str(a.id),
                "title": a.title,
                "status": a.status,
                "action": a.action,
                "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
                "review_notes": a.review_notes,
                "reviewed_by_name": reviewer_name,
            }
            for a, reviewer_name in entity_result.all()
        ]

        seen = {a.get("approval_id") for a in linked}
        merged = list(linked)
        for a in entity_approvals:
            if a["approval_id"] not in seen:
                merged.append(a)

        approval_ids = [a.get("approval_id") for a in merged if a.get("approval_id")]
        if approval_ids:
            reviewer_map = await self._reviewer_names(approval_ids)
            for a in merged:
                if not a.get("reviewed_by_name"):
                    a["reviewed_by_name"] = reviewer_map.get(a.get("approval_id"))

        return merged

    async def _reviewer_names(self, approval_ids: list[str]) -> dict[str, str | None]:
        from uuid import UUID as PyUUID

        ids = [PyUUID(aid) for aid in approval_ids if aid]
        result = await self.db.execute(
            select(ApprovalQueue.id, User.full_name)
            .outerjoin(User, ApprovalQueue.reviewed_by == User.id)
            .where(ApprovalQueue.id.in_(ids))
        )
        return {str(row[0]): row[1] for row in result.all()}

    async def _get_workflow(self, workflow_id: UUID, tenant_id: UUID) -> Workflow:
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        return workflow
