from typing import Type

from backend.connectors.base import BaseConnector, ConnectorConfig


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, Type[BaseConnector]] = {}
        self._instances: dict[str, BaseConnector] = {}

    def register(self, connector_class: Type[BaseConnector]) -> Type[BaseConnector]:
        self._connectors[connector_class.name] = connector_class
        return connector_class

    def get_class(self, name: str) -> Type[BaseConnector]:
        if name not in self._connectors:
            raise KeyError(f"Connector '{name}' not registered")
        return self._connectors[name]

    def create_instance(self, name: str, config: ConnectorConfig) -> BaseConnector:
        connector_class = self.get_class(name)
        instance = connector_class(config)
        self._instances[f"{name}:{config.endpoint}"] = instance
        return instance

    def list_connectors(self) -> list[dict]:
        return [
            {
                "name": cls.name,
                "type": cls.connector_type.value,
                "description": cls.description,
                "version": cls.version,
            }
            for cls in self._connectors.values()
        ]


connector_registry = ConnectorRegistry()
