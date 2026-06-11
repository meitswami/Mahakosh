from typing import Type

from backend.connectors.accounting.base.connector import BaseAccountingConnector
from backend.connectors.accounting.base.types import AccountingConnectorType


class AccountingConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, Type[BaseAccountingConnector]] = {}

    def register(self, connector_class: Type[BaseAccountingConnector]) -> Type[BaseAccountingConnector]:
        self._connectors[connector_class.connector_type.value] = connector_class
        return connector_class

    def get_class(self, connector_type: str) -> Type[BaseAccountingConnector]:
        if connector_type not in self._connectors:
            raise KeyError(f"Accounting connector '{connector_type}' not registered")
        return self._connectors[connector_type]

    def create_instance(self, connector_type: str, config: dict) -> BaseAccountingConnector:
        connector_class = self.get_class(connector_type)
        return connector_class(config)

    def list_connectors(self) -> list[dict]:
        return [
            {
                "connector_type": cls.connector_type.value,
                "name": cls.name,
                "description": cls.description,
                "version": cls.version,
                "priority": cls.priority,
                "supported_erp_systems": cls.supported_erp_systems,
            }
            for cls in sorted(self._connectors.values(), key=lambda c: c.priority)
        ]

    @property
    def registered_types(self) -> list[str]:
        return list(self._connectors.keys())


accounting_connector_registry = AccountingConnectorRegistry()
