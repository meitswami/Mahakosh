"""Accounting Draft Engine — creates voucher drafts for all standard types."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any


class AccountingDraftEngine:
    VOUCHER_TYPES = ("purchase", "sales", "receipt", "payment", "journal", "contra")

    def create_purchase_draft(self, data: dict[str, Any]) -> dict[str, Any]:
        amount = Decimal(str(data.get("amount", data.get("subtotal", 0))))
        vendor = data.get("vendor_name", data.get("party", "Vendor"))
        gst_rate = Decimal(str(data.get("gst_rate", 18)))
        tax = amount * gst_rate / 100
        cgst = tax / 2
        sgst = tax / 2
        total = amount + tax
        return self._build_draft("purchase", vendor, amount, cgst, sgst, Decimal(0), total, [
            {"ledger": "Purchase Account", "debit": float(amount), "credit": 0},
            {"ledger": "Input CGST", "debit": float(cgst), "credit": 0},
            {"ledger": "Input SGST", "debit": float(sgst), "credit": 0},
            {"ledger": vendor, "debit": 0, "credit": float(total)},
        ], data)

    def create_sales_draft(self, data: dict[str, Any]) -> dict[str, Any]:
        amount = Decimal(str(data.get("amount", data.get("subtotal", 0))))
        customer = data.get("customer_name", data.get("party", "Customer"))
        gst_rate = Decimal(str(data.get("gst_rate", 18)))
        tax = amount * gst_rate / 100
        cgst = tax / 2
        sgst = tax / 2
        total = amount + tax
        return self._build_draft("sales", customer, amount, cgst, sgst, Decimal(0), total, [
            {"ledger": customer, "debit": float(total), "credit": 0},
            {"ledger": "Sales Account", "debit": 0, "credit": float(amount)},
            {"ledger": "Output CGST", "debit": 0, "credit": float(cgst)},
            {"ledger": "Output SGST", "debit": 0, "credit": float(sgst)},
        ], data)

    def create_receipt_draft(self, data: dict[str, Any]) -> dict[str, Any]:
        amount = Decimal(str(data.get("amount", 0)))
        party = data.get("party", "Customer")
        bank = data.get("bank_ledger", "Bank Account")
        return self._build_draft("receipt", party, amount, Decimal(0), Decimal(0), Decimal(0), amount, [
            {"ledger": bank, "debit": float(amount), "credit": 0},
            {"ledger": party, "debit": 0, "credit": float(amount)},
        ], data)

    def create_payment_draft(self, data: dict[str, Any]) -> dict[str, Any]:
        amount = Decimal(str(data.get("amount", 0)))
        party = data.get("party", "Vendor")
        bank = data.get("bank_ledger", "Bank Account")
        return self._build_draft("payment", party, amount, Decimal(0), Decimal(0), Decimal(0), amount, [
            {"ledger": party, "debit": float(amount), "credit": 0},
            {"ledger": bank, "debit": 0, "credit": float(amount)},
        ], data)

    def create_journal_draft(self, data: dict[str, Any]) -> dict[str, Any]:
        lines = data.get("lines", [])
        total_debit = sum(Decimal(str(l.get("debit", 0))) for l in lines)
        return self._build_draft("journal", data.get("party"), total_debit, Decimal(0), Decimal(0), Decimal(0), total_debit, lines, data)

    def create_contra_draft(self, data: dict[str, Any]) -> dict[str, Any]:
        amount = Decimal(str(data.get("amount", 0)))
        from_ledger = data.get("from_ledger", "Cash")
        to_ledger = data.get("to_ledger", "Bank Account")
        return self._build_draft("contra", None, amount, Decimal(0), Decimal(0), Decimal(0), amount, [
            {"ledger": to_ledger, "debit": float(amount), "credit": 0},
            {"ledger": from_ledger, "debit": 0, "credit": float(amount)},
        ], data)

    def create_draft(self, voucher_type: str, data: dict[str, Any]) -> dict[str, Any]:
        creators = {
            "purchase": self.create_purchase_draft,
            "sales": self.create_sales_draft,
            "receipt": self.create_receipt_draft,
            "payment": self.create_payment_draft,
            "journal": self.create_journal_draft,
            "contra": self.create_contra_draft,
        }
        creator = creators.get(voucher_type.lower())
        if not creator:
            raise ValueError(f"Unsupported voucher type: {voucher_type}")
        return creator(data)

    def _build_draft(
        self,
        voucher_type: str,
        party: str | None,
        subtotal: Decimal,
        cgst: Decimal,
        sgst: Decimal,
        igst: Decimal,
        total: Decimal,
        lines: list[dict[str, Any]],
        source_data: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "voucher_type": voucher_type,
            "voucher_date": source_data.get("voucher_date", date.today().isoformat()),
            "party_name": party,
            "party_gstin": source_data.get("party_gstin"),
            "subtotal": float(subtotal),
            "cgst_amount": float(cgst),
            "sgst_amount": float(sgst),
            "igst_amount": float(igst),
            "total_amount": float(total),
            "narration": source_data.get("narration", f"{voucher_type.title()} voucher"),
            "lines": lines,
            "status": "draft",
            "validation_status": "pending",
            "approval_status": "pending",
            "export_status": "not_exported",
        }
