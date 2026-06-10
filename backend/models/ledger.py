from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Ledger(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ledgers"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    parent_group: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ledger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    tally_ledger_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
