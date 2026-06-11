from typing import Any

from backend.connectors.accounting.base.types import CompanyInfo, LedgerInfo, StockItemInfo


class TallyODBCDriver:
    """ODBC driver wrapper for Tally — requires pyodbc and Tally ODBC driver on Windows."""

    def __init__(self, dsn: str = "TallyODBC64_9000", connection_string: str | None = None):
        self.dsn = dsn
        self.connection_string = connection_string or f"DSN={dsn}"
        self._connection = None

    def _get_pyodbc(self):
        try:
            import pyodbc
            return pyodbc
        except ImportError:
            return None

    def connect(self) -> tuple[bool, str | None]:
        pyodbc = self._get_pyodbc()
        if pyodbc is None:
            return False, "pyodbc not installed. Install pyodbc and Tally ODBC driver for ODBC connectivity."
        try:
            self._connection = pyodbc.connect(self.connection_string, timeout=10)
            return True, None
        except Exception as exc:
            return False, str(exc)

    def disconnect(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    def health_check(self) -> dict[str, Any]:
        ok, error = self.connect()
        if not ok:
            return {"healthy": False, "error": error}
        try:
            cursor = self._connection.cursor()
            cursor.execute("SELECT $Name FROM Company")
            row = cursor.fetchone()
            self.disconnect()
            return {"healthy": True, "company": row[0] if row else None, "dsn": self.dsn}
        except Exception as exc:
            self.disconnect()
            return {"healthy": False, "error": str(exc)}

    def list_companies(self) -> list[CompanyInfo]:
        pyodbc = self._get_pyodbc()
        if not pyodbc or not self._connection:
            return []
        try:
            cursor = self._connection.cursor()
            cursor.execute("SELECT $Name, $BooksFrom, $StartingFrom FROM Company")
            companies = []
            for row in cursor.fetchall():
                companies.append(
                    CompanyInfo(
                        name=str(row[0]),
                        books_begin_from=None,
                        metadata={"source": "tally_odbc", "dsn": self.dsn},
                    )
                )
            return companies
        except Exception:
            return []

    def list_ledgers(self) -> list[LedgerInfo]:
        if not self._connection:
            return []
        try:
            cursor = self._connection.cursor()
            cursor.execute("SELECT $Name, $_PrimaryGroup, $OpeningBalance FROM Ledger")
            return [
                LedgerInfo(
                    name=str(row[0]),
                    parent_group=str(row[1]) if row[1] else None,
                    opening_balance=row[2] if row[2] is not None else 0,
                    metadata={"source": "tally_odbc"},
                )
                for row in cursor.fetchall()
            ]
        except Exception:
            return []

    def list_stock_items(self) -> list[StockItemInfo]:
        if not self._connection:
            return []
        try:
            cursor = self._connection.cursor()
            cursor.execute("SELECT $Name, $BaseUnits, $OpeningBalance FROM StockItem")
            return [
                StockItemInfo(
                    name=str(row[0]),
                    unit=str(row[1]) if row[1] else "NOS",
                    opening_stock=row[2] if row[2] is not None else 0,
                    metadata={"source": "tally_odbc"},
                )
                for row in cursor.fetchall()
            ]
        except Exception:
            return []
