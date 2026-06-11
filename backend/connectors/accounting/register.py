"""Register all accounting connectors on import."""

import backend.connectors.accounting.base.future_erp_connector  # noqa: F401
import backend.connectors.accounting.odbc.tally_odbc_connector  # noqa: F401
import backend.connectors.accounting.sync.file_sync_connector  # noqa: F401
import backend.connectors.accounting.tally.tally_xml_connector  # noqa: F401
from backend.connectors.accounting.base.registry import accounting_connector_registry

__all__ = ["accounting_connector_registry"]
