"""Normalized accounting domain objects — independent of Tally/ERP structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class TwinObjectType(StrEnum):
    COMPANY = "company"
    LEDGER = "ledger"
    LEDGER_GROUP = "ledger_group"
    STOCK_ITEM = "stock_item"
    UNIT = "unit"
    VOUCHER = "voucher"
    VOUCHER_LINE = "voucher_line"
    PARTY = "party"
    GST_PROFILE = "gst_profile"
    OUTSTANDING = "outstanding"


class IssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class TwinIssue:
    code: str
    message: str
    severity: IssueSeverity = IssueSeverity.WARNING
    field: str | None = None
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "field": self.field,
            "suggestion": self.suggestion,
        }


@dataclass
class TwinObjectBase:
    """Base for all normalized accounting objects in the digital twin."""

    source_system: str
    source_id: str
    raw_payload: dict[str, Any]
    normalized_fields: dict[str, Any]
    quality_score: float = 100.0
    issues: list[TwinIssue] = field(default_factory=list)
    normalization_notes: list[str] = field(default_factory=list)
    object_type: TwinObjectType = TwinObjectType.LEDGER
    id: UUID | None = None
    connector_id: UUID | None = None
    sync_job_id: UUID | None = None

    @property
    def display_name(self) -> str:
        return (
            self.normalized_fields.get("name")
            or self.normalized_fields.get("party_name")
            or self.normalized_fields.get("voucher_number")
            or self.source_id
        )

    def add_issue(
        self,
        code: str,
        message: str,
        severity: IssueSeverity = IssueSeverity.WARNING,
        field: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.issues.append(TwinIssue(code, message, severity, field, suggestion))

    def add_note(self, note: str) -> None:
        if note not in self.normalization_notes:
            self.normalization_notes.append(note)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id) if self.id else None,
            "object_type": self.object_type.value,
            "source_system": self.source_system,
            "source_id": self.source_id,
            "display_name": self.display_name,
            "raw_payload": self.raw_payload,
            "normalized_fields": self.normalized_fields,
            "quality_score": self.quality_score,
            "issues": [i.to_dict() for i in self.issues],
            "normalization_notes": self.normalization_notes,
            "connector_id": str(self.connector_id) if self.connector_id else None,
            "sync_job_id": str(self.sync_job_id) if self.sync_job_id else None,
        }


@dataclass
class NormalizedCompany(TwinObjectBase):
    object_type: TwinObjectType = field(default=TwinObjectType.COMPANY, init=False)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], source_system: str) -> NormalizedCompany:
        name = raw.get("name", "")
        return cls(
            source_system=source_system,
            source_id=raw.get("id") or raw.get("guid") or name,
            raw_payload=raw,
            normalized_fields={
                "name": name,
                "financial_year": raw.get("financial_year"),
                "books_begin_from": raw.get("books_begin_from"),
                "books_status": raw.get("books_status"),
                "gstin": raw.get("gstin"),
                "state": raw.get("state"),
            },
        )


@dataclass
class NormalizedLedger(TwinObjectBase):
    object_type: TwinObjectType = field(default=TwinObjectType.LEDGER, init=False)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], source_system: str) -> NormalizedLedger:
        name = raw.get("name", "")
        return cls(
            source_system=source_system,
            source_id=raw.get("id") or raw.get("guid") or name,
            raw_payload=raw,
            normalized_fields={
                "name": name,
                "parent_group": raw.get("parent_group"),
                "ledger_type": raw.get("ledger_type", "general"),
                "opening_balance": float(raw.get("opening_balance", 0)),
                "current_balance": float(raw.get("current_balance", raw.get("opening_balance", 0))),
                "gstin": raw.get("gstin"),
                "pan": raw.get("pan"),
                "address": raw.get("address"),
                "is_active": raw.get("is_active", True),
            },
        )


@dataclass
class NormalizedLedgerGroup(TwinObjectBase):
    object_type: TwinObjectType = field(default=TwinObjectType.LEDGER_GROUP, init=False)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], source_system: str) -> NormalizedLedgerGroup:
        name = raw.get("name", "")
        return cls(
            source_system=source_system,
            source_id=raw.get("id") or raw.get("guid") or name,
            raw_payload=raw,
            normalized_fields={
                "name": name,
                "parent_group": raw.get("parent_group"),
                "group_type": raw.get("group_type", "general"),
            },
        )


@dataclass
class NormalizedStockItem(TwinObjectBase):
    object_type: TwinObjectType = field(default=TwinObjectType.STOCK_ITEM, init=False)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], source_system: str) -> NormalizedStockItem:
        name = raw.get("name", "")
        return cls(
            source_system=source_system,
            source_id=raw.get("id") or raw.get("guid") or name,
            raw_payload=raw,
            normalized_fields={
                "name": name,
                "unit": raw.get("unit", "NOS"),
                "hsn_code": raw.get("hsn_code"),
                "gst_rate": float(raw["gst_rate"]) if raw.get("gst_rate") is not None else None,
                "rate": float(raw["rate"]) if raw.get("rate") is not None else None,
                "category": raw.get("category"),
                "sku": raw.get("sku"),
                "opening_qty": float(raw.get("opening_qty", 0)),
                "closing_qty": float(raw.get("closing_qty", raw.get("opening_qty", 0))),
            },
        )


@dataclass
class NormalizedUnit(TwinObjectBase):
    object_type: TwinObjectType = field(default=TwinObjectType.UNIT, init=False)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], source_system: str) -> NormalizedUnit:
        name = raw.get("name", "")
        return cls(
            source_system=source_system,
            source_id=raw.get("id") or raw.get("guid") or name,
            raw_payload=raw,
            normalized_fields={
                "name": name,
                "symbol": raw.get("symbol", name),
                "decimal_places": raw.get("decimal_places", 2),
            },
        )


@dataclass
class NormalizedVoucherLine(TwinObjectBase):
    object_type: TwinObjectType = field(default=TwinObjectType.VOUCHER_LINE, init=False)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], source_system: str, voucher_id: str) -> NormalizedVoucherLine:
        return cls(
            source_system=source_system,
            source_id=raw.get("id") or f"{voucher_id}:{raw.get('ledger_name', '')}:{raw.get('amount', 0)}",
            raw_payload=raw,
            normalized_fields={
                "ledger_name": raw.get("ledger_name"),
                "item_name": raw.get("item_name"),
                "amount": float(raw.get("amount", 0)),
                "debit": float(raw.get("debit", 0)),
                "credit": float(raw.get("credit", 0)),
                "hsn_code": raw.get("hsn_code"),
                "gst_rate": float(raw["gst_rate"]) if raw.get("gst_rate") is not None else None,
                "quantity": float(raw["quantity"]) if raw.get("quantity") is not None else None,
            },
        )


@dataclass
class NormalizedVoucher(TwinObjectBase):
    object_type: TwinObjectType = field(default=TwinObjectType.VOUCHER, init=False)
    lines: list[NormalizedVoucherLine] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], source_system: str) -> NormalizedVoucher:
        vch_id = raw.get("id") or raw.get("guid") or raw.get("voucher_number", "")
        obj = cls(
            source_system=source_system,
            source_id=str(vch_id),
            raw_payload=raw,
            normalized_fields={
                "voucher_type": raw.get("voucher_type", "unknown"),
                "voucher_number": raw.get("voucher_number"),
                "voucher_date": raw.get("voucher_date"),
                "party_name": raw.get("party_name"),
                "party_gstin": raw.get("party_gstin"),
                "subtotal": float(raw.get("subtotal", 0)),
                "cgst_amount": float(raw.get("cgst_amount", 0)),
                "sgst_amount": float(raw.get("sgst_amount", 0)),
                "igst_amount": float(raw.get("igst_amount", 0)),
                "total_amount": float(raw.get("total_amount", 0)),
                "narration": raw.get("narration"),
                "status": raw.get("status", "imported"),
            },
        )
        for line_raw in raw.get("lines", []):
            obj.lines.append(NormalizedVoucherLine.from_raw(line_raw, source_system, str(vch_id)))
        return obj


@dataclass
class NormalizedParty(TwinObjectBase):
    object_type: TwinObjectType = field(default=TwinObjectType.PARTY, init=False)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], source_system: str, party_type: str = "general") -> NormalizedParty:
        name = raw.get("name", "")
        return cls(
            source_system=source_system,
            source_id=raw.get("id") or raw.get("guid") or name,
            raw_payload=raw,
            normalized_fields={
                "name": name,
                "party_type": raw.get("party_type", party_type),
                "gstin": raw.get("gstin"),
                "pan": raw.get("pan"),
                "address": raw.get("address"),
                "state": raw.get("state"),
                "contact": raw.get("contact"),
            },
        )


@dataclass
class NormalizedGSTProfile(TwinObjectBase):
    object_type: TwinObjectType = field(default=TwinObjectType.GST_PROFILE, init=False)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], source_system: str) -> NormalizedGSTProfile:
        gstin = raw.get("gstin", "")
        return cls(
            source_system=source_system,
            source_id=raw.get("id") or gstin or raw.get("name", ""),
            raw_payload=raw,
            normalized_fields={
                "gstin": gstin,
                "legal_name": raw.get("legal_name") or raw.get("name"),
                "trade_name": raw.get("trade_name"),
                "registration_type": raw.get("registration_type"),
                "state_code": gstin[:2] if len(gstin) >= 2 else None,
                "default_gst_rate": float(raw["default_gst_rate"]) if raw.get("default_gst_rate") is not None else None,
            },
        )


@dataclass
class NormalizedOutstanding(TwinObjectBase):
    object_type: TwinObjectType = field(default=TwinObjectType.OUTSTANDING, init=False)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], source_system: str) -> NormalizedOutstanding:
        party = raw.get("party_name") or raw.get("name", "")
        return cls(
            source_system=source_system,
            source_id=raw.get("id") or f"{party}:{raw.get('bill_ref', '')}",
            raw_payload=raw,
            normalized_fields={
                "party_name": party,
                "party_type": raw.get("party_type", "unknown"),
                "bill_ref": raw.get("bill_ref"),
                "bill_date": raw.get("bill_date"),
                "due_date": raw.get("due_date"),
                "amount": float(raw.get("amount", 0)),
                "outstanding_type": raw.get("outstanding_type", "receivable"),
            },
        )
