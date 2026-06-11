from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


class VoucherDraftEngine:
    """Generate accounting voucher drafts from invoice/OCR data."""

    VOUCHER_TYPES = {
        "purchase": "Purchase",
        "purchase_invoice": "Purchase",
        "sales": "Sales",
        "sales_invoice": "Sales",
        "receipt": "Receipt",
        "payment": "Payment",
        "journal": "Journal",
        "contra": "Contra",
    }

    @classmethod
    def _money(cls, value: float | Decimal) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def detect_voucher_type(cls, document_type: str) -> str:
        doc_lower = document_type.lower()
        for key, vch_type in cls.VOUCHER_TYPES.items():
            if key in doc_lower:
                return vch_type
        return "Journal"

    @classmethod
    def build_purchase_voucher(cls, data: dict[str, Any]) -> dict[str, Any]:
        amount = cls._money(data.get("subtotal") or data.get("amount") or 0)
        gst_rate = float(data.get("gst_rate", 18))
        cgst = cls._money(amount * Decimal(str(gst_rate)) / 200)
        sgst = cgst
        igst = cls._money(0) if not data.get("inter_state") else cls._money(amount * Decimal(str(gst_rate)) / 100)
        total = amount + cgst + sgst + igst
        vendor = data.get("vendor_name") or data.get("party_name", "Unknown Vendor")

        lines = [
            {"ledger": "Purchase Account", "debit": float(amount), "credit": 0, "amount": float(amount)},
        ]
        if igst > 0:
            lines.append({"ledger": "Input IGST", "debit": float(igst), "credit": 0, "amount": float(igst)})
        else:
            lines.extend([
                {"ledger": "Input CGST", "debit": float(cgst), "credit": 0, "amount": float(cgst)},
                {"ledger": "Input SGST", "debit": float(sgst), "credit": 0, "amount": float(sgst)},
            ])
        lines.append({"ledger": vendor, "debit": 0, "credit": float(total), "amount": float(total)})

        inventory_lines = []
        for item in data.get("line_items", data.get("items", [])):
            inventory_lines.append({
                "item_name": item.get("name") or item.get("description", ""),
                "quantity": float(item.get("quantity", 1)),
                "rate": float(item.get("rate", 0)),
                "amount": float(item.get("amount", 0)),
                "hsn_code": item.get("hsn_code"),
            })

        return {
            "voucher_type": "Purchase",
            "voucher_date": data.get("voucher_date", date.today().isoformat()),
            "party_name": vendor,
            "party_gstin": data.get("party_gstin") or data.get("gstin"),
            "subtotal": float(amount),
            "cgst_amount": float(cgst),
            "sgst_amount": float(sgst),
            "igst_amount": float(igst),
            "total_amount": float(total),
            "narration": data.get("narration", f"Purchase from {vendor}"),
            "lines": lines,
            "inventory_lines": inventory_lines,
            "status": "draft",
        }

    @classmethod
    def build_sales_voucher(cls, data: dict[str, Any]) -> dict[str, Any]:
        amount = cls._money(data.get("subtotal") or data.get("amount") or 0)
        gst_rate = float(data.get("gst_rate", 18))
        cgst = cls._money(amount * Decimal(str(gst_rate)) / 200)
        sgst = cgst
        igst = cls._money(0) if not data.get("inter_state") else cls._money(amount * Decimal(str(gst_rate)) / 100)
        total = amount + cgst + sgst + igst
        customer = data.get("customer_name") or data.get("party_name", "Unknown Customer")

        lines = [
            {"ledger": customer, "debit": float(total), "credit": 0, "amount": float(total)},
            {"ledger": "Sales Account", "debit": 0, "credit": float(amount), "amount": float(amount)},
        ]
        if igst > 0:
            lines.append({"ledger": "Output IGST", "debit": 0, "credit": float(igst), "amount": float(igst)})
        else:
            lines.extend([
                {"ledger": "Output CGST", "debit": 0, "credit": float(cgst), "amount": float(cgst)},
                {"ledger": "Output SGST", "debit": 0, "credit": float(sgst), "amount": float(sgst)},
            ])

        return {
            "voucher_type": "Sales",
            "voucher_date": data.get("voucher_date", date.today().isoformat()),
            "party_name": customer,
            "party_gstin": data.get("party_gstin") or data.get("gstin"),
            "subtotal": float(amount),
            "cgst_amount": float(cgst),
            "sgst_amount": float(sgst),
            "igst_amount": float(igst),
            "total_amount": float(total),
            "narration": data.get("narration", f"Sales to {customer}"),
            "lines": lines,
            "status": "draft",
        }

    @classmethod
    def build_receipt_voucher(cls, data: dict[str, Any]) -> dict[str, Any]:
        amount = cls._money(data.get("amount") or data.get("total_amount", 0))
        party = data.get("party_name", "Customer")
        bank = data.get("bank_ledger", "Bank Account")
        return {
            "voucher_type": "Receipt",
            "voucher_date": data.get("voucher_date", date.today().isoformat()),
            "party_name": party,
            "total_amount": float(amount),
            "narration": data.get("narration", f"Receipt from {party}"),
            "lines": [
                {"ledger": bank, "debit": float(amount), "credit": 0, "amount": float(amount)},
                {"ledger": party, "debit": 0, "credit": float(amount), "amount": float(amount)},
            ],
            "status": "draft",
        }

    @classmethod
    def build_payment_voucher(cls, data: dict[str, Any]) -> dict[str, Any]:
        amount = cls._money(data.get("amount") or data.get("total_amount", 0))
        party = data.get("party_name", "Vendor")
        bank = data.get("bank_ledger", "Bank Account")
        return {
            "voucher_type": "Payment",
            "voucher_date": data.get("voucher_date", date.today().isoformat()),
            "party_name": party,
            "total_amount": float(amount),
            "narration": data.get("narration", f"Payment to {party}"),
            "lines": [
                {"ledger": party, "debit": float(amount), "credit": 0, "amount": float(amount)},
                {"ledger": bank, "debit": 0, "credit": float(amount), "amount": float(amount)},
            ],
            "status": "draft",
        }

    @classmethod
    def build_journal_voucher(cls, data: dict[str, Any]) -> dict[str, Any]:
        lines = data.get("lines", [])
        total_debit = sum(l.get("debit", 0) for l in lines)
        return {
            "voucher_type": "Journal",
            "voucher_date": data.get("voucher_date", date.today().isoformat()),
            "total_amount": total_debit,
            "narration": data.get("narration", "Journal entry"),
            "lines": lines,
            "status": "draft",
        }

    @classmethod
    def build_contra_voucher(cls, data: dict[str, Any]) -> dict[str, Any]:
        amount = cls._money(data.get("amount") or data.get("total_amount", 0))
        from_ledger = data.get("from_ledger", "Cash")
        to_ledger = data.get("to_ledger", "Bank Account")
        return {
            "voucher_type": "Contra",
            "voucher_date": data.get("voucher_date", date.today().isoformat()),
            "total_amount": float(amount),
            "narration": data.get("narration", f"Transfer from {from_ledger} to {to_ledger}"),
            "lines": [
                {"ledger": to_ledger, "debit": float(amount), "credit": 0, "amount": float(amount)},
                {"ledger": from_ledger, "debit": 0, "credit": float(amount), "amount": float(amount)},
            ],
            "status": "draft",
        }

    @classmethod
    def generate(cls, data: dict[str, Any]) -> dict[str, Any]:
        doc_type = data.get("document_type", data.get("voucher_type", "purchase"))
        vch_type = cls.detect_voucher_type(str(doc_type))

        builders = {
            "Purchase": cls.build_purchase_voucher,
            "Sales": cls.build_sales_voucher,
            "Receipt": cls.build_receipt_voucher,
            "Payment": cls.build_payment_voucher,
            "Journal": cls.build_journal_voucher,
            "Contra": cls.build_contra_voucher,
        }
        builder = builders.get(vch_type, cls.build_journal_voucher)
        return builder(data)
