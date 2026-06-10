from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

import structlog

from backend.agents.base.types import AgentContext, AgentHealthReport, AgentResult, AgentStatus

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """Abstract base for all Mahakosh agents.

    Agents must consume data only through tools (Knowledge, Workflow, Approval APIs).
    """

    name: str = "base_agent"
    version: str = "1.0.0"
    description: str = ""
    capabilities: list[str] = []
    requires_approval_for: list[str] = []

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name
        self.status = AgentStatus.IDLE
        self._initialized = False
        self._execution_count = 0
        self._success_count = 0
        self._total_runtime_ms = 0
        self._last_error: str | None = None
        self._queue_length = 0
        self._logger = logger.bind(agent=self.name)

    async def initialize(self) -> None:
        """Prepare agent resources. Override for model/tool warmup."""
        self._initialized = True
        self.status = AgentStatus.IDLE

    @abstractmethod
    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        """Execute the agent's primary task."""

    async def validate(self, input_data: dict[str, Any], context: AgentContext) -> tuple[bool, str]:
        """Validate inputs before execution. Returns (ok, message)."""
        if not input_data and self.name not in ("master_orchestrator", "search"):
            return False, "input_data is required"
        return True, ""

    async def report(self, result: AgentResult, context: AgentContext) -> dict[str, Any]:
        """Produce observability report for an execution."""
        return {
            "agent": self.name,
            "version": self.version,
            "tenant_id": str(context.tenant_id),
            "execution_id": str(context.execution_id) if context.execution_id else None,
            "success": result.success,
            "confidence": result.confidence,
            "confidence_level": result.confidence_level.value,
            "reasoning_summary": result.reasoning[:500] if result.reasoning else "",
            "sources_count": len(result.sources),
            "processing_time_ms": result.processing_time_ms,
        }

    async def health_check(self) -> AgentHealthReport:
        avg = (
            self._total_runtime_ms / self._execution_count
            if self._execution_count > 0
            else 0.0
        )
        success_rate = (
            (self._success_count / self._execution_count) * 100
            if self._execution_count > 0
            else 100.0
        )
        healthy = self.status not in (AgentStatus.FAILED, AgentStatus.SHUTDOWN) and success_rate >= 50
        return AgentHealthReport(
            agent_name=self.name,
            status=self.status,
            healthy=healthy,
            execution_count=self._execution_count,
            success_rate=round(success_rate, 2),
            average_runtime_ms=round(avg, 2),
            queue_length=self._queue_length,
            last_error=self._last_error,
        )

    async def shutdown(self) -> None:
        self.status = AgentStatus.SHUTDOWN
        self._initialized = False

    async def pre_execute(self, input_data: dict[str, Any], context: AgentContext) -> dict[str, Any]:
        return input_data

    async def post_execute(self, result: AgentResult, context: AgentContext) -> AgentResult:
        return result

    async def run(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        if not self._initialized:
            await self.initialize()

        start_time = datetime.now(UTC)
        self.status = AgentStatus.RUNNING
        self._queue_length += 1
        self._logger.info("agent_execution_started", tenant_id=str(context.tenant_id))

        try:
            valid, msg = await self.validate(input_data, context)
            if not valid:
                return AgentResult(success=False, error=msg or "Validation failed", confidence=0.0)

            processed = await self.pre_execute(input_data, context)
            result = await self.execute(processed, context)
            result = await self.post_execute(result, context)

            elapsed = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            result.processing_time_ms = result.processing_time_ms or elapsed

            self._execution_count += 1
            self._total_runtime_ms += result.processing_time_ms
            if result.success:
                self._success_count += 1
                self.status = AgentStatus.IDLE
            else:
                self._last_error = result.error
                self.status = AgentStatus.FAILED

            self._logger.info(
                "agent_execution_completed",
                success=result.success,
                confidence=result.confidence,
                processing_time_ms=result.processing_time_ms,
            )
            return result

        except Exception as exc:
            self.status = AgentStatus.FAILED
            self._last_error = str(exc)
            elapsed = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            self._execution_count += 1
            self._total_runtime_ms += elapsed
            self._logger.error("agent_execution_failed", error=str(exc))
            return AgentResult(
                success=False,
                error=str(exc),
                confidence=0.0,
                processing_time_ms=elapsed,
            )
        finally:
            self._queue_length = max(0, self._queue_length - 1)

    def get_info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "requires_approval_for": self.requires_approval_for,
            "execution_count": self._execution_count,
            "success_rate": round(
                (self._success_count / self._execution_count * 100) if self._execution_count else 100.0,
                2,
            ),
            "average_runtime_ms": round(
                self._total_runtime_ms / self._execution_count if self._execution_count else 0.0,
                2,
            ),
        }
