import time
from typing import Any
from uuid import UUID

from backend.agents.base.agent import BaseAgent
from backend.agents.base.types import AgentContext, AgentEventType, AgentResult, ExecutionMode
from backend.agents.communication.event_bus import event_bus
from backend.agents.consensus.engine import ConsensusVote, consensus_engine
from backend.agents.memory.task_memory import task_memory
from backend.agents.memory.workflow_memory import workflow_memory
from backend.agents.orchestrator.decomposer import task_decomposer
from backend.agents.orchestrator.execution_engine import execution_engine


class MasterOrchestratorAgent(BaseAgent):
    name = "master_orchestrator"
    version = "2.0.0"
    description = "Central brain — task decomposition, agent coordination, result merging"
    capabilities = [
        "orchestration",
        "task_decomposition",
        "agent_routing",
        "parallel_execution",
        "batch_execution",
        "consensus_merging",
    ]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        start = time.perf_counter()
        task_type = input_data.get("task_type", "general")
        payload = input_data.get("payload", input_data)
        execution_mode = input_data.get("execution_mode", "sequential")
        tenant_str = str(context.tenant_id)

        task = task_memory.create(tenant_str, task_type, payload)
        context.task_id = task.task_id
        task_memory.update(tenant_str, task.task_id, status="running")

        plan = task_decomposer.decompose(task_type, payload)
        unique_agents = list(dict.fromkeys(st.agent_name for st in plan.subtasks))

        await event_bus.broadcast(
            context.tenant_id,
            self.name,
            AgentEventType.AGENT_STARTED,
            {"task_type": task_type, "agents": unique_agents, "task_id": task.task_id},
        )

        if execution_mode == "parallel" or plan.execution_mode == "parallel":
            results_map = await execution_engine.run_parallel(unique_agents, payload, context, self.model_name)
        elif plan.execution_mode == "batch" and payload.get("items"):
            batch_results: dict[str, Any] = {}
            for agent in unique_agents:
                items = payload.get("items", [])
                batch = await execution_engine.run_batch(agent, items, context, self.model_name)
                batch_results[agent] = [r.to_output_dict() for r in batch]
            results_map = {}
            for agent, batch in batch_results.items():
                success = all(b.get("success") for b in batch) if batch else False
                results_map[agent] = AgentResult(
                    success=success,
                    data={"batch_results": batch, "count": len(batch)},
                    confidence=sum(b.get("confidence", 0) for b in batch) / len(batch) if batch else 0,
                )
        else:
            results_map = await execution_engine.run_sequential(unique_agents, payload, context, self.model_name)

        merged = self._merge_results(results_map)
        consensus = self._build_consensus(results_map)

        if context.workflow_id:
            workflow_memory.record_step(
                tenant_str,
                str(context.workflow_id),
                self.name,
                {"task_type": task_type, "agents": unique_agents},
                merged,
            )

        errors = [f"{n}: {r.error}" for n, r in results_map.items() if not r.success and r.error]
        all_success = len(errors) == 0
        avg_confidence = (
            sum(r.confidence for r in results_map.values()) / len(results_map)
            if results_map else 0.0
        )

        task_memory.update(tenant_str, task.task_id, status="completed" if all_success else "failed", outputs=merged)

        await event_bus.broadcast(
            context.tenant_id,
            self.name,
            AgentEventType.WORKFLOW_COMPLETED if all_success else AgentEventType.AGENT_FAILED,
            {"task_id": task.task_id, "task_type": task_type, "success": all_success},
        )

        elapsed = int((time.perf_counter() - start) * 1000)
        return AgentResult(
            success=all_success,
            data={
                "task_id": task.task_id,
                "task_type": task_type,
                "plan": plan.description,
                "agent_results": {n: r.to_output_dict() for n, r in results_map.items()},
                "merged": merged,
                "consensus": [c.to_dict() for c in consensus],
            },
            confidence=round(avg_confidence, 2),
            reasoning=f"Executed {len(unique_agents)} agents in {plan.execution_mode} mode for {task_type}",
            error="; ".join(errors) if errors else None,
            processing_time_ms=elapsed,
        )

    def _merge_results(self, results: dict[str, AgentResult]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for name, result in results.items():
            if result.success:
                merged[name] = result.data
        return merged

    def _build_consensus(self, results: dict[str, AgentResult]) -> list:
        field_votes: dict[str, list[ConsensusVote]] = {}
        consensus_fields = ("gst_rate", "total_amount", "vendor_name", "gstin", "hsn_code")
        for agent_name, result in results.items():
            if not result.success:
                continue
            for field in consensus_fields:
                if field in result.data:
                    field_votes.setdefault(field, []).append(
                        ConsensusVote(agent_name, field, result.data[field], result.confidence, result.reasoning)
                    )
        return consensus_engine.compute_batch(field_votes)
