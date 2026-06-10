from typing import Type

import structlog

from backend.agents.base.agent import BaseAgent

logger = structlog.get_logger(__name__)


class AgentRegistry:
    """Plugin-based dynamic agent registry."""

    def __init__(self) -> None:
        self._agents: dict[str, Type[BaseAgent]] = {}
        self._instances: dict[str, BaseAgent] = {}

    def register(self, agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"{agent_class} must inherit from BaseAgent")
        self._agents[agent_class.name] = agent_class
        logger.info("agent_registered", name=agent_class.name, version=agent_class.version)
        return agent_class

    def unregister(self, name: str) -> None:
        self._agents.pop(name, None)
        keys_to_remove = [k for k in self._instances if k.startswith(f"{name}:")]
        for k in keys_to_remove:
            del self._instances[k]

    def get_class(self, name: str) -> Type[BaseAgent]:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not registered")
        return self._agents[name]

    def get_instance(self, name: str, model_name: str | None = None) -> BaseAgent:
        cache_key = f"{name}:{model_name or 'default'}"
        if cache_key not in self._instances:
            agent_class = self.get_class(name)
            self._instances[cache_key] = agent_class(model_name=model_name)
        return self._instances[cache_key]

    def list_agents(self) -> list[dict]:
        result = []
        for cls in self._agents.values():
            try:
                instance = self.get_instance(cls.name)
                info = instance.get_info()
            except Exception:
                info = {
                    "name": cls.name,
                    "version": cls.version,
                    "description": cls.description,
                    "capabilities": cls.capabilities,
                    "status": "unknown",
                }
            result.append(info)
        return result

    async def health_check_all(self) -> list[dict]:
        reports = []
        for cls in self._agents.values():
            instance = self.get_instance(cls.name)
            report = await instance.health_check()
            reports.append({
                "agent_name": report.agent_name,
                "status": report.status.value,
                "healthy": report.healthy,
                "execution_count": report.execution_count,
                "success_rate": report.success_rate,
                "average_runtime_ms": report.average_runtime_ms,
                "queue_length": report.queue_length,
                "last_error": report.last_error,
            })
        return reports

    @property
    def registered_names(self) -> list[str]:
        return list(self._agents.keys())

    def discover_plugins(self, module_path: str = "backend.agents.specialists") -> None:
        import importlib
        import pkgutil

        try:
            package = importlib.import_module(module_path)
            for _, name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
                importlib.import_module(name)
        except ImportError as exc:
            logger.warning("plugin_discovery_failed", module=module_path, error=str(exc))


agent_registry = AgentRegistry()
