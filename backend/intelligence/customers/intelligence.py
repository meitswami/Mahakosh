"""Customer intelligence — revenue contribution, outstanding, risk scoring."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.intelligence.analytics.aggregators import (
    apply_share_pct,
    group_by_month,
    in_period,
    recent_period_cutoff,
    sum_field,
    top_n_by_field,
    trend_series,
)
from backend.intelligence.analytics.data_source import IntelligenceDataContext


class CustomerIntelligence:
    def analyze(self, ctx: IntelligenceDataContext) -> dict[str, Any]:
        sales = ctx.sales_vouchers
        top_customers = apply_share_pct(top_n_by_field(sales, "party_name", "total_amount", 15))
        if not top_customers:
            top_customers = apply_share_pct(top_n_by_field(sales, "party_name", "subtotal", 15))

        revenue_trend = group_by_month(sales, "voucher_date", "total_amount")
        if not revenue_trend:
            revenue_trend = group_by_month(sales, "voucher_date", "subtotal")

        outstanding_by_customer = apply_share_pct(top_n_by_field(ctx.receivables, "party_name", "amount", 15))
        risk_scores = self._risk_scoring(sales, ctx.receivables, top_customers)

        return {
            "top_customers": top_customers,
            "revenue_contribution": {
                "top5_share_pct": round(sum(c["share_pct"] for c in top_customers[:5]), 2),
                "total_customers": len({s.get("party_name") for s in sales if s.get("party_name")}),
            },
            "customer_trends": trend_series(revenue_trend),
            "outstanding_payments": outstanding_by_customer,
            "total_receivables": sum_field(ctx.receivables, "amount"),
            "risk_scores": risk_scores[:15],
        }

    def _risk_scoring(
        self,
        sales: list[dict],
        receivables: list[dict],
        top_customers: list[dict],
    ) -> list[dict[str, Any]]:
        receivable_map: dict[str, float] = defaultdict(float)
        for r in receivables:
            receivable_map[r.get("party_name", "Unknown")] += float(r.get("amount", 0))

        revenue_map = {c["name"]: c["value"] for c in top_customers}
        cutoff = recent_period_cutoff(90)
        recent_sales: dict[str, float] = defaultdict(float)
        for s in sales:
            if in_period(s, "voucher_date", cutoff):
                recent_sales[s.get("party_name", "Unknown")] += float(s.get("total_amount") or s.get("subtotal") or 0)

        scores: list[dict[str, Any]] = []
        all_customers = set(revenue_map) | set(receivable_map)
        for name in all_customers:
            revenue = revenue_map.get(name, 0)
            outstanding = receivable_map.get(name, 0)
            recent = recent_sales.get(name, 0)

            risk = 0
            if revenue > 0 and outstanding / revenue > 0.5:
                risk += 40
            elif revenue > 0 and outstanding / revenue > 0.25:
                risk += 25
            if outstanding > 100000:
                risk += 20
            if recent == 0 and outstanding > 0:
                risk += 30

            risk = min(100, risk)
            level = "high" if risk >= 60 else "medium" if risk >= 30 else "low"
            scores.append({
                "customer": name,
                "risk_score": risk,
                "risk_level": level,
                "revenue": revenue,
                "outstanding": outstanding,
                "recent_activity": recent > 0,
            })

        return sorted(scores, key=lambda x: x["risk_score"], reverse=True)
