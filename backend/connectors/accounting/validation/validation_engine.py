"""Accounting validation engine — validates drafts before approval."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


class ValidationEngine:
    def validate_voucher_draft(self, voucher: dict[str, Any]) -> dict[str, Any]:
        issues: list[dict[str, str]] = []
        checks_passed: list[str] = []

        voucher_type = voucher.get("voucher_type", "")
        if voucher_type:
            checks_passed.append("voucher_type_present")
        else:
            issues.append({"field": "voucher_type", "message": "Voucher type is required"})

        total = Decimal(str(voucher.get("total_amount", voucher.get("total", 0))))
        if total > 0:
            checks_passed.append("positive_total")
        else:
            issues.append({"field": "total_amount", "message": "Total amount must be positive"})

        lines = voucher.get("lines", [])
        if lines:
            debit_sum = sum(Decimal(str(l.get("debit", 0))) for l in lines)
            credit_sum = sum(Decimal(str(l.get("credit", 0))) for l in lines)
            if abs(debit_sum - credit_sum) < Decimal("0.01"):
                checks_passed.append("balanced_entries")
            else:
                issues.append({
                    "field": "lines",
                    "message": f"Debit ({debit_sum}) != Credit ({credit_sum})",
                })
        else:
            checks_passed.append("single_sided_voucher")

        party = voucher.get("party_name") or voucher.get("party")
        if party:
            checks_passed.append("party_present")
        elif voucher_type in ("purchase", "sales", "receipt", "payment"):
            issues.append({"field": "party", "message": "Party name required for this voucher type"})

        gst_total = (
            Decimal(str(voucher.get("cgst_amount", 0)))
            + Decimal(str(voucher.get("sgst_amount", 0)))
            + Decimal(str(voucher.get("igst_amount", 0)))
        )
        if gst_total >= 0:
            checks_passed.append("gst_amounts_valid")

        is_valid = len(issues) == 0
        confidence = 95.0 if is_valid else max(40.0, 95.0 - len(issues) * 15)

        return {
            "is_valid": is_valid,
            "status": "passed" if is_valid else "failed",
            "issues": issues,
            "checks_passed": checks_passed,
            "confidence": confidence,
            "reasoning": "All validation checks passed" if is_valid else f"{len(issues)} validation issue(s) found",
        }

    def validate_ledger_mapping(self, mapping: dict[str, Any]) -> dict[str, Any]:
        issues = []
        checks_passed = []
        if mapping.get("external_name"):
            checks_passed.append("external_name_present")
        else:
            issues.append({"field": "external_name", "message": "External name required"})
        confidence = float(mapping.get("confidence", 0))
        if confidence >= 80:
            checks_passed.append("high_confidence")
        elif confidence >= 60:
            checks_passed.append("medium_confidence")
        else:
            issues.append({"field": "confidence", "message": f"Low confidence: {confidence}%"})
        return {
            "is_valid": len(issues) == 0,
            "status": "passed" if not issues else "warning",
            "issues": issues,
            "checks_passed": checks_passed,
            "confidence": confidence,
        }

    def validate_export_readiness(self, voucher: dict[str, Any], validation: dict[str, Any], approval_status: str) -> dict[str, Any]:
        issues = []
        checks_passed = []
        if validation.get("is_valid"):
            checks_passed.append("validation_passed")
        else:
            issues.append({"field": "validation", "message": "Validation not passed"})
        if approval_status == "approved":
            checks_passed.append("approval_granted")
        else:
            issues.append({"field": "approval", "message": f"Approval status: {approval_status}"})
        if voucher.get("status") not in ("rejected", "cancelled"):
            checks_passed.append("voucher_active")
        return {
            "is_valid": len(issues) == 0,
            "status": "ready" if not issues else "blocked",
            "issues": issues,
            "checks_passed": checks_passed,
            "reasoning": "Export ready" if not issues else "Export blocked by approval gate",
        }
