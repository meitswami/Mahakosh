"""GST Intelligence — liability analysis and compliance insights."""

from __future__ import annotations

from typing import Any


class GSTIntelligence:
    name = "gst_intelligence"
    version = "1.0.0"

    def analyze_liability(self, vouchers: list[dict[str, Any]], period: str | None = None) -> dict[str, Any]:
        output_cgst = output_sgst = output_igst = 0.0
        input_cgst = input_sgst = input_igst = 0.0

        for vch in vouchers:
            vch_type = (vch.get("voucher_type") or "").lower()
            cgst = float(vch.get("cgst_amount", 0))
            sgst = float(vch.get("sgst_amount", 0))
            igst = float(vch.get("igst_amount", 0))
            if vch_type == "sales":
                output_cgst += cgst
                output_sgst += sgst
                output_igst += igst
            elif vch_type == "purchase":
                input_cgst += cgst
                input_sgst += sgst
                input_igst += igst

        net_cgst = output_cgst - input_cgst
        net_sgst = output_sgst - input_sgst
        net_igst = output_igst - input_igst
        net_liability = net_cgst + net_sgst + net_igst

        return {
            "agent": self.name,
            "period": period,
            "output_tax": {"cgst": round(output_cgst, 2), "sgst": round(output_sgst, 2), "igst": round(output_igst, 2)},
            "input_tax": {"cgst": round(input_cgst, 2), "sgst": round(input_sgst, 2), "igst": round(input_igst, 2)},
            "net_liability": round(net_liability, 2),
            "confidence": 88.0,
            "reasoning": f"Net GST liability ₹{net_liability:,.2f} for period {period or 'all'}",
        }

    def hsn_summary(self, voucher_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
        hsn_map: dict[str, dict[str, Any]] = {}
        for line in voucher_lines:
            hsn = line.get("hsn_code") or "UNKNOWN"
            if hsn not in hsn_map:
                hsn_map[hsn] = {"hsn": hsn, "taxable_value": 0, "tax": 0, "count": 0}
            hsn_map[hsn]["taxable_value"] += float(line.get("amount", 0))
            hsn_map[hsn]["tax"] += float(line.get("cgst_amount", 0)) + float(line.get("sgst_amount", 0)) + float(line.get("igst_amount", 0))
            hsn_map[hsn]["count"] += 1
        return sorted(hsn_map.values(), key=lambda x: x["taxable_value"], reverse=True)
