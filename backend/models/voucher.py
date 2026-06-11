import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class VoucherDraft(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "voucher_drafts"

    voucher_type: Mapped[str] = mapped_column(String(50), nullable=False)
    voucher_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    voucher_date: Mapped[date] = mapped_column(Date, nullable=False)
    party_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    party_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    connector_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_connectors.id", ondelete="SET NULL"), nullable=True
    )
    validation_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    approval_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    export_status: Mapped[str] = mapped_column(String(50), default="not_exported", nullable=False)
    narration: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    lines = relationship("VoucherLine", back_populates="voucher", cascade="all, delete-orphan")


class VoucherLine(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "voucher_lines"

    voucher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voucher_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    hsn_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=1, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="NOS", nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    gst_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    ledger_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ledgers.id", ondelete="SET NULL"), nullable=True
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    voucher = relationship("VoucherDraft", back_populates="lines")
