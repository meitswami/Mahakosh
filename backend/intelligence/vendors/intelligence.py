"""Vendor intelligence — concentration, trends, duplicates, inactive."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.intelligence.analytics.aggregators import (
    apply_share_pct,
    group_by_month,
    in_period,
    recent_period_cutoff,
    top_n_by_field,
    trend_series,
)
from backend.intelligence.analytics.data_source import IntelligenceDataContext


class VendorIntelligence:
    def analyze(self, ctx: IntelligenceDataContext) -> dict[str, Any]:
        purchases = ctx.purchase_vouchers
        vendor_parties = [p for p in ctx.parties if (p.get("party_type") or "").lower() in ("vendor", "creditor", "supplier")]
        if not vendor_parties:
            vendor_parties = [{"name": v.get("party_name"), "gstin": v.get("party_gstin")} for v in purchases if v.get("party_name")]

        top_vendors = apply_share_pct(top_n_by_field(purchases, "party_name", "total_amount", 15))
        if not top_vendors:
            top_vendors = apply_share_pct(top_n_by_field(purchases, "party_name", "subtotal", 15))

        purchase_trend = group_by_month(purchases, "voucher_date", "total_amount")
        if not purchase_trend:
            purchase_trend = group_by_month(purchases, "voucher_date", "subtotal")

        concentration = self._concentration_risk(top_vendors)
        inactive = self._inactive_vendors(purchases, vendor_parties)
        duplicates = self._duplicate_vendors(vendor_parties)
        dependency = self._dependency_analysis(top_vendors)

        return {
            "top_vendors": top_vendors,
            "purchase_trends": trend_series(purchase_trend),
            "concentration_risk": concentration,
            "vendor_dependency": dependency,
            "inactive_vendors": inactive[:15],
            "duplicate_vendors": duplicates[:10],
            "total_vendors": len({v.get("party_name") for v in purchases if v.get("party_name")}),
            "total_purchase_value": sum(v["value"] for v in top_vendors) if top_vendors else 0,
        }

    def _concentration_risk(self, top_vendors: list[dict]) -> dict[str, Any]:
        if not top_vendors:
            return {"level": "low", "top3_share_pct": 0, "message": "No vendor purchase data"}
        top3 = sum(v["share_pct"] for v in top_vendors[:3])
        level = "high" if top3 >= 70 else "medium" if top3 >= 50 else "low"
        return {
            "level": level,
            "top3_share_pct": round(top3, 2),
            "top_vendor": top_vendors[0]["name"] if top_vendors else None,
            "top_vendor_share_pct": top_vendors[0]["share_pct"] if top_vendors else 0,
            "message": f"Top 3 vendors account for {top3:.1f}% of purchases",
        }

    def _inactive_vendors(
        self,
        purchases: list[dict],
        parties: list[dict],
    ) -> list[dict[str, Any]]:
        cutoff = recent_period_cutoff(180)
        active = {v.get("party_name") for v in purchases if in_period(v, "voucher_date", cutoff)}
        inactive: list[dict[str, Any]] = []
        for p in parties:
            name = p.get("name")
            if name and name not in active:
                inactive.append({"name": name, "gstin": p.get("gstin"), "last_active": "180+ days ago"})
        return inactive

    def _duplicate_vendors(self, parties: list[dict]) -> list[dict[str, Any]]:
        by_gstin: dict[str, list[str]] = defaultdict(list)
        by_name: dict[str, list[str]] = defaultdict(list)
        for p in parties:
            name = (p.get("name") or "").strip()
            gstin = (p.get("gstin") or "").strip().upper()
            if gstin:
                by_gstin[gstin].append(name)
            if name:
                by_name[name.lower()].append(name)

        dupes: list[dict[str, Any]] = []
        for gstin, names in by_gstin.items():
            unique = list(set(names))
            if len(unique) > 1:
                dupes.append({"type": "same_gstin", "gstin": gstin, "names": unique})
        return dupes

    def _dependency_analysis(self, top_vendors: list[dict]) -> list[dict[str, Any]]:
        return [
            {
                "vendor": v["name"],
                "purchase_value": v["value"],
                "share_pct": v["share_pct"],
                "risk": "critical" if v["share_pct"] >= 40 else "elevated" if v["share_pct"] >= 25 else "normal",
            }
            for v in top_vendors[:5]
        ]
