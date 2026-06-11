from typing import Type

from backend.connectors.accounting.base.base_accounting_connector import (
    AccountingConnectorConfig,
    AccountingConnectorType,
    BaseAccountingConnector,
)
from backend.connectors.accounting.file_sync_connector import FileSyncConnector
from backend.connectors.accounting.future_erp_connector import FutureERPConnector
from backend.connectors.accounting.tally.tally_odbc_connector import TallyODBCConnector
from backend.connectors.accounting.tally.tally_xml_connector import TallyXMLConnector


class AccountingConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, Type[BaseAccountingConnector]] = {}
        self._by_type: dict[AccountingConnectorType, Type[BaseAccountingConnector]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for cls in (TallyXMLConnector, TallyODBCConnector, FileSyncConnector, FutureERPConnector):
            self.register(cls)

    def register(self, connector_class: Type[BaseAccountingConnector]) -> Type[BaseAccountingConnector]:
        self._connectors[connector_class.name] = connector_class
        self._by_type[connector_class.connector_type] = connector_class
        return connector_class

    def get_class(self, name: str) -> Type[BaseAccountingConnector]:
        if name not in self._connectors:
            raise KeyError(f"Accounting connector '{name}' not registered")
        return self._connectors[name]

    def get_by_type(self, connector_type: AccountingConnectorType) -> Type[BaseAccountingConnector]:
        if connector_type not in self._by_type:
            raise KeyError(f"No connector for type '{connector_type.value}'")
        return self._by_type[connector_type]

    def create(self, config: AccountingConnectorConfig) -> BaseAccountingConnector:
        connector_class = self.get_by_type(config.connector_type)
        return connector_class(config)

    def create_from_db_record(self, record: dict) -> BaseAccountingConnector:
        connector_type = AccountingConnectorType(record["connector_type"])
        config = AccountingConnectorConfig(
            name=record["name"],
            connector_type=connector_type,
            endpoint=record.get("config", {}).get("endpoint"),
            company_name=record.get("config", {}).get("company_name"),
            credentials=record.get("config", {}).get("credentials", {}),
            options=record.get("config", {}).get("options", {}),
            priority=record.get("priority", 1),
        )
        return self.create(config)

    def list_connectors(self) -> list[dict]:
        return sorted(
            [
                {
                    "name": cls.name,
                    "type": cls.connector_type.value,
                    "description": cls.description,
                    "version": cls.version,
                    "priority": cls.priority,
                }
                for cls in self._connectors.values()
            ],
            key=lambda x: x["priority"],
        )


accounting_connector_registry = AccountingConnectorRegistry()
