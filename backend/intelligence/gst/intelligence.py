"""GST intelligence — liability, collections, trends, anomalies."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.connectors.accounting.intelligence.gst_intelligence import GSTIntelligence
from backend.intelligence.analytics.aggregators import group_by_month, trend_series
from backend.intelligence.analytics.data_source import IntelligenceDataContext


class GSTIntelligenceModule:
    def analyze(self, ctx: IntelligenceDataContext) -> dict[str, Any]:
        gst = GSTIntelligence()
        liability = gst.liability_summary(ctx.all_vouchers)

        monthly_output: dict[str, float] = defaultdict(float)
        monthly_input: dict[str, float] = defaultdict(float)
        for v in ctx.all_vouchers:
            month_series = group_by_month([v], "voucher_date", "total_amount")
            if not month_series:
                continue
            month = next(iter(month_series))
            tax = float(v.get("cgst_amount", 0)) + float(v.get("sgst_amount", 0)) + float(v.get("igst_amount", 0))
            vch_type = (v.get("voucher_type") or "").lower()
            if "sales" in vch_type:
                monthly_output[month] += tax
            elif "purchase" in vch_type:
                monthly_input[month] += tax

        net_monthly: dict[str, float] = {}
        for m in sorted(set(monthly_output) | set(monthly_input)):
            net_monthly[m] = round(monthly_output.get(m, 0) - monthly_input.get(m, 0), 2)

        anomalies = self._detect_mismatches(ctx)
        cleanups = self._inline_cleanups(ctx)

        return {
            "liability": liability,
            "collections": {
                "output_tax_total": liability["output_tax"]["total"],
                "input_tax_total": liability["input_tax"]["total"],
                "net_liability": liability["net_liability"],
            },
            "trends": {
                "output_tax": trend_series(dict(sorted(monthly_output.items()))),
                "input_tax": trend_series(dict(sorted(monthly_input.items()))),
                "net_liability": trend_series(net_monthly),
            },
            "anomalies": anomalies,
            "cleanup_suggestions": cleanups[:10],
            "voucher_count": len(ctx.all_vouchers),
        }

    def _detect_mismatches(self, ctx: IntelligenceDataContext) -> list[dict[str, Any]]:
        anomalies: list[dict[str, Any]] = []
        seen: dict[str, list[str]] = defaultdict(list)

        for v in ctx.all_vouchers:
            num = v.get("voucher_number")
            if num:
                seen[str(num)].append(str(v.get("id", "")))

            subtotal = float(v.get("subtotal", 0))
            gst_total = float(v.get("cgst_amount", 0)) + float(v.get("sgst_amount", 0)) + float(v.get("igst_amount", 0))
            if subtotal > 1000 and gst_total == 0:
                anomalies.append({
                    "type": "missing_gst",
                    "severity": "high",
                    "voucher_number": v.get("voucher_number"),
                    "party_name": v.get("party_name"),
                    "amount": subtotal,
                    "message": f"Voucher {v.get('voucher_number')} has ₹{subtotal:,.0f} but no GST",
                })

            cgst = float(v.get("cgst_amount", 0))
            sgst = float(v.get("sgst_amount", 0))
            igst = float(v.get("igst_amount", 0))
            if cgst > 0 and sgst > 0 and igst > 0:
                anomalies.append({
                    "type": "cgst_sgst_igst_conflict",
                    "severity": "medium",
                    "voucher_number": v.get("voucher_number"),
                    "message": "Both intra-state (CGST+SGST) and IGST present on same voucher",
                })

        for num, ids in seen.items():
            if len(ids) > 1:
                anomalies.append({
                    "type": "duplicate_voucher_number",
                    "severity": "high",
                    "voucher_number": num,
                    "count": len(ids),
                    "message": f"Voucher number '{num}' appears {len(ids)} times",
                })

        return anomalies[:20]

    def _inline_cleanups(self, ctx: IntelligenceDataContext) -> list[dict[str, Any]]:
        suggestions: list[dict[str, Any]] = []
        for v in ctx.all_vouchers:
            gstin = v.get("party_gstin")
            if gstin and len(str(gstin)) != 15:
                suggestions.append({
                    "type": "invalid_gstin",
                    "priority": "high",
                    "message": f"Invalid GSTIN on voucher {v.get('voucher_number')}: {gstin}",
                })
        return suggestions
