import re
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.connectors.accounting.twin.repository import TwinRepository
from backend.connectors.accounting.twin.reality import IndianAccountingReality
from backend.connectors.accounting.validation.validator import AccountingValidator


class GSTIntelligence:
    """GST validation and liability — operates on digital twin voucher data."""

    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self.reality = IndianAccountingReality()
        self.twin_repo = TwinRepository(db) if db else None

    @classmethod
    def validate_invoice(cls, invoice_data: dict[str, Any]) -> dict[str, Any]:
        issues = []
        checks_passed = []

        vendor_gstin = invoice_data.get("vendor_gstin") or invoice_data.get("party_gstin")
        customer_gstin = invoice_data.get("customer_gstin")
        issues.extend(AccountingValidator.validate_gstin(vendor_gstin, "Vendor GSTIN"))
        if customer_gstin:
            issues.extend(AccountingValidator.validate_gstin(customer_gstin, "Customer GSTIN"))
        else:
            checks_passed.append("customer_gstin_optional")

        gst_rate = invoice_data.get("gst_rate")
        issues.extend(AccountingValidator.validate_gst_rate(gst_rate))
        if gst_rate is not None:
            checks_passed.append("gst_rate_checked")

        subtotal = float(invoice_data.get("subtotal") or invoice_data.get("amount") or 0)
        if subtotal > 0:
            issues.extend(AccountingValidator.validate_tax_amounts(
                subtotal,
                float(invoice_data.get("cgst_amount", 0)),
                float(invoice_data.get("sgst_amount", 0)),
                float(invoice_data.get("igst_amount", 0)),
                float(gst_rate or 18),
                invoice_data.get("inter_state", False),
            ))
            checks_passed.append("tax_amounts_validated")

        for idx, line in enumerate(invoice_data.get("line_items", invoice_data.get("items", []))):
            hsn_issues = AccountingValidator.validate_hsn(line.get("hsn_code"))
            for issue in hsn_issues:
                issue.field = f"line_items[{idx}].hsn_code"
            issues.extend(hsn_issues)

        is_valid = not any(i.severity == "error" for i in issues)
        return {
            "is_valid": is_valid,
            "issues": [
                {"code": i.code, "message": i.message, "severity": i.severity, "field": i.field}
                for i in issues
            ],
            "checks_passed": checks_passed,
            "confidence": max(0, 100 - len(issues) * 8),
            "vendor_gstin_valid": vendor_gstin and bool(
                re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", vendor_gstin.upper())
            ),
            "customer_gstin_valid": customer_gstin and bool(
                re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", customer_gstin.upper())
            ) if customer_gstin else None,
        }

    @classmethod
    def compute_tax(cls, amount: float, gst_rate: float, inter_state: bool = False) -> dict[str, float]:
        tax = round(amount * gst_rate / 100, 2)
        if inter_state:
            return {"cgst": 0.0, "sgst": 0.0, "igst": tax, "total_tax": tax}
        half = round(tax / 2, 2)
        return {"cgst": half, "sgst": half, "igst": 0.0, "total_tax": tax}

    @classmethod
    def liability_summary(cls, vouchers: list[dict[str, Any]]) -> dict[str, Any]:
        output_cgst = output_sgst = output_igst = 0.0
        input_cgst = input_sgst = input_igst = 0.0
        for v in vouchers:
            vch_type = (v.get("voucher_type") or "").lower()
            cgst = float(v.get("cgst_amount", 0))
            sgst = float(v.get("sgst_amount", 0))
            igst = float(v.get("igst_amount", 0))
            if "sales" in vch_type:
                output_cgst += cgst
                output_sgst += sgst
                output_igst += igst
            elif "purchase" in vch_type:
                input_cgst += cgst
                input_sgst += sgst
                input_igst += igst
        return {
            "output_tax": {
                "cgst": round(output_cgst, 2),
                "sgst": round(output_sgst, 2),
                "igst": round(output_igst, 2),
                "total": round(output_cgst + output_sgst + output_igst, 2),
            },
            "input_tax": {
                "cgst": round(input_cgst, 2),
                "sgst": input_sgst,
                "igst": round(input_igst, 2),
                "total": round(input_cgst + input_sgst + input_igst, 2),
            },
            "net_liability": round(
                (output_cgst + output_sgst + output_igst) - (input_cgst + input_sgst + input_igst), 2
            ),
        }

    async def liability_from_twin(self, tenant_id: UUID) -> dict[str, Any]:
        """Compute GST liability from normalized twin vouchers."""
        if not self.twin_repo:
            return self.liability_summary([])
        vouchers = await self.twin_repo.get_twin_dicts(tenant_id, "voucher")
        return self.liability_summary(vouchers)

    async def suggest_cleanups(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """Suggest GST-related cleanups from twin data."""
        if not self.twin_repo:
            return []
        suggestions: list[dict[str, Any]] = []
        vouchers = await self.twin_repo.get_twin_dicts(tenant_id, "voucher")
        for v in vouchers:
            party_gstin = v.get("party_gstin")
            if party_gstin:
                valid, msg = self.reality.validate_gstin(party_gstin)
                if not valid:
                    suggestions.append({
                        "type": "invalid_gstin",
                        "priority": "high",
                        "message": f"Voucher {v.get('voucher_number', 'N/A')}: {msg}",
                        "action": "fix_gstin",
                        "details": {"voucher_id": v.get("id")},
                    })
            gst_total = float(v.get("cgst_amount", 0)) + float(v.get("sgst_amount", 0)) + float(v.get("igst_amount", 0))
            subtotal = float(v.get("subtotal", 0))
            if subtotal > 0 and gst_total == 0:
                suggestions.append({
                    "type": "missing_gst",
                    "priority": "medium",
                    "message": f"Voucher {v.get('voucher_number', 'N/A')} has amount but no GST",
                    "action": "review_gst",
                    "details": {"voucher_id": v.get("id")},
                })

        items = await self.twin_repo.get_twin_dicts(tenant_id, "stock_item")
        for item in items:
            rate = item.get("gst_rate")
            if rate is not None:
                valid, msg = self.reality.validate_gst_rate(rate)
                if not valid:
                    suggestions.append({
                        "type": "non_standard_rate",
                        "priority": "low",
                        "message": f"Item '{item.get('name')}': {msg}",
                        "action": "fix_gst_rate",
                        "details": {"item_id": item.get("id"), "current_rate": rate},
                    })
        return suggestions

    async def top_vendors_by_outstanding(self, tenant_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
        """Top vendors/customers by outstanding from twin data."""
        if not self.twin_repo:
            return []
        outstanding = await self.twin_repo.get_twin_dicts(tenant_id, "outstanding")
        party_totals: dict[str, float] = {}
        for o in outstanding:
            party = o.get("party_name", "Unknown")
            party_totals[party] = party_totals.get(party, 0) + float(o.get("amount", 0))
        sorted_parties = sorted(party_totals.items(), key=lambda x: x[1], reverse=True)
        return [{"party_name": name, "amount": amt} for name, amt in sorted_parties[:limit]]
