"""Anomaly detection across financial, GST, and vendor data."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.intelligence.analytics.aggregators import sum_field
from backend.intelligence.analytics.data_source import IntelligenceDataContext
from backend.intelligence.gst.intelligence import GSTIntelligenceModule


class AnomalyDetector:
    def detect(self, ctx: IntelligenceDataContext) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        events.extend(self._unusual_purchases(ctx))
        events.extend(self._duplicate_invoices(ctx))
        events.extend(self._suspicious_vendors(ctx))
        events.extend(self._gst_mismatches(ctx))
        events.extend(self._abnormal_spending(ctx))
        return sorted(events, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 4))

    def _unusual_purchases(self, ctx: IntelligenceDataContext) -> list[dict[str, Any]]:
        purchases = ctx.purchase_vouchers
        if len(purchases) < 3:
            return []
        amounts = [float(p.get("total_amount") or p.get("subtotal") or 0) for p in purchases]
        avg = sum(amounts) / len(amounts)
        threshold = avg * 3
        events = []
        for p in purchases:
            amt = float(p.get("total_amount") or p.get("subtotal") or 0)
            if amt > threshold and amt > 50000:
                events.append({
                    "type": "unusual_purchase",
                    "severity": "high",
                    "entity_type": "voucher",
                    "entity_id": p.get("id"),
                    "title": f"Unusual purchase: ₹{amt:,.0f}",
                    "description": f"Purchase from {p.get('party_name')} is {amt/avg:.1f}x average",
                    "amount": amt,
                    "party_name": p.get("party_name"),
                })
        return events

    def _duplicate_invoices(self, ctx: IntelligenceDataContext) -> list[dict[str, Any]]:
        seen: dict[str, list[dict]] = defaultdict(list)
        for v in ctx.all_vouchers:
            key = f"{v.get('party_name')}:{v.get('voucher_number')}:{v.get('total_amount')}"
            seen[key].append(v)
        events = []
        for key, group in seen.items():
            if len(group) > 1:
                events.append({
                    "type": "duplicate_invoice",
                    "severity": "critical",
                    "entity_type": "voucher",
                    "title": f"Duplicate invoice detected",
                    "description": f"{len(group)} vouchers match {key}",
                    "count": len(group),
                })
        return events

    def _suspicious_vendors(self, ctx: IntelligenceDataContext) -> list[dict[str, Any]]:
        events = []
        for p in ctx.parties:
            gstin = p.get("gstin")
            if gstin and len(str(gstin)) != 15:
                events.append({
                    "type": "suspicious_vendor",
                    "severity": "high",
                    "entity_type": "party",
                    "entity_id": p.get("id"),
                    "title": f"Invalid GSTIN: {p.get('name')}",
                    "description": f"GSTIN '{gstin}' does not match standard format",
                })
        return events

    def _gst_mismatches(self, ctx: IntelligenceDataContext) -> list[dict[str, Any]]:
        gst_anomalies = GSTIntelligenceModule().analyze(ctx).get("anomalies", [])
        return [
            {
                "type": "gst_mismatch",
                "severity": a.get("severity", "medium"),
                "entity_type": "voucher",
                "title": a.get("message", "GST mismatch"),
                "description": a.get("message"),
                "voucher_number": a.get("voucher_number"),
            }
            for a in gst_anomalies
        ]

    def _abnormal_spending(self, ctx: IntelligenceDataContext) -> list[dict[str, Any]]:
        purchases = ctx.purchase_vouchers
        vendor_totals: dict[str, float] = defaultdict(float)
        for p in purchases:
            vendor_totals[p.get("party_name", "Unknown")] += float(p.get("total_amount") or p.get("subtotal") or 0)
        total = sum(vendor_totals.values())
        if total <= 0:
            return []
        events = []
        for vendor, amt in vendor_totals.items():
            share = amt / total
            if share > 0.5 and amt > 100000:
                events.append({
                    "type": "abnormal_spending",
                    "severity": "medium",
                    "entity_type": "vendor",
                    "title": f"High vendor concentration: {vendor}",
                    "description": f"{vendor} accounts for {share*100:.1f}% of total purchases (₹{amt:,.0f})",
                    "amount": amt,
                    "share_pct": round(share * 100, 1),
                })
        return events
