import asyncio
from typing import Any
from uuid import UUID

import structlog

from backend.agents.base.types import AgentContext, AgentResult, ExecutionMode
from backend.agents.registry.registry import agent_registry

logger = structlog.get_logger(__name__)


class AgentExecutionEngine:
    """Runs agent tasks sequentially, in parallel, or in batches."""

    def __init__(self, max_parallel: int = 10, max_retries: int = 2):
        self.max_parallel = max_parallel
        self.max_retries = max_retries

    async def run_agent(
        self,
        agent_name: str,
        input_data: dict[str, Any],
        context: AgentContext,
        model_name: str | None = None,
    ) -> AgentResult:
        agent = agent_registry.get_instance(agent_name, model_name)
        last_result: AgentResult | None = None

        for attempt in range(self.max_retries + 1):
            result = await agent.run(input_data, context)
            last_result = result
            if result.success:
                return result
            if attempt < self.max_retries:
                logger.warning("agent_retry", agent=agent_name, attempt=attempt + 1)

        if last_result and not last_result.success:
            fallback = self._get_fallback_agent(agent_name)
            if fallback:
                logger.info("agent_fallback", from_agent=agent_name, to_agent=fallback)
                return await self.run_agent(fallback, input_data, context, model_name)

        return last_result or AgentResult(success=False, error="Execution failed", confidence=0.0)

    async def run_sequential(
        self,
        agent_names: list[str],
        input_data: dict[str, Any],
        context: AgentContext,
        model_name: str | None = None,
    ) -> dict[str, AgentResult]:
        results: dict[str, AgentResult] = {}
        payload = dict(input_data)
        for name in agent_names:
            result = await self.run_agent(name, payload, context, model_name)
            results[name] = result
            if result.success:
                payload = {**payload, **result.data}
            else:
                break
        return results

    async def run_parallel(
        self,
        agent_names: list[str],
        input_data: dict[str, Any],
        context: AgentContext,
        model_name: str | None = None,
    ) -> dict[str, AgentResult]:
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def _run(name: str) -> tuple[str, AgentResult]:
            async with semaphore:
                result = await self.run_agent(name, input_data, context, model_name)
                return name, result

        pairs = await asyncio.gather(*[_run(n) for n in agent_names], return_exceptions=True)
        results: dict[str, AgentResult] = {}
        for pair in pairs:
            if isinstance(pair, Exception):
                continue
            name, result = pair
            results[name] = result
        return results

    async def run_batch(
        self,
        agent_name: str,
        items: list[dict[str, Any]],
        context: AgentContext,
        model_name: str | None = None,
        mode: ExecutionMode = ExecutionMode.PARALLEL,
    ) -> list[AgentResult]:
        if mode == ExecutionMode.SEQUENTIAL:
            results = []
            for item in items:
                results.append(await self.run_agent(agent_name, item, context, model_name))
            return results

        semaphore = asyncio.Semaphore(self.max_parallel)

        async def _run(item: dict[str, Any]) -> AgentResult:
            async with semaphore:
                return await self.run_agent(agent_name, item, context, model_name)

        return list(await asyncio.gather(*[_run(i) for i in items]))

    def _get_fallback_agent(self, agent_name: str) -> str | None:
        fallbacks = {
            "ocr": "validation",
            "gst": "validation",
            "hsn": "gst",
            "accounting": "validation",
            "vendor": "search",
            "item": "search",
            "tally": "approval",
        }
        return fallbacks.get(agent_name)


execution_engine = AgentExecutionEngine()
