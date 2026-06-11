"""Financial recommendations capability — profit, expense, cash optimization."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from backend.cfo.capabilities.base import BaseCFOCapability
from backend.cfo.types import CFOCapabilityType, CFORecommendation, CapabilityResult, RecommendationPriority
from backend.intelligence.analytics.data_source import IntelligenceDataContext


class FinancialRecommendationsCapability(BaseCFOCapability):
    capability_type = CFOCapabilityType.FINANCIAL_RECOMMENDATIONS

    async def analyze(
        self,
        tenant_id: UUID,
        ctx: IntelligenceDataContext,
        financial: dict[str, Any],
        workflow: dict[str, Any],
        health: dict[str, Any],
    ) -> CapabilityResult:
        summary = financial.get("summary", {})
        growth = financial.get("growth", {})
        items = []
        recs = []

        margin = summary.get("profit_margin_pct", 0)
        if margin < 10 and summary.get("revenue", 0) > 0:
            items.append({
                "type": "low_margin",
                "message": f"Profit margin is {margin}% — below healthy threshold",
                "severity": "high",
            })

        exp_growth = growth.get("expense_pct")
        rev_growth = growth.get("revenue_pct")
        if exp_growth is not None and rev_growth is not None and exp_growth > rev_growth + 5:
            items.append({
                "type": "expense_outpacing_revenue",
                "message": f"Expenses grew {exp_growth}% vs revenue {rev_growth}%",
                "severity": "high",
            })

        payables = summary.get("payables", 0)
        receivables = summary.get("receivables", 0)
        if payables > receivables * 1.5 and payables > 50000:
            items.append({
                "type": "payables_pressure",
                "message": f"Payables (₹{payables:,.0f}) exceed receivables — cash flow risk",
                "severity": "medium",
            })

        analysis = CapabilityResult(
            capability=self.capability_type,
            status="active" if items else "healthy",
            summary=f"{len(items)} financial optimization opportunities identified",
            items=items,
            metrics={
                "revenue": summary.get("revenue", 0),
                "profit_margin_pct": margin,
                "cash_position": summary.get("cash_position", 0),
            },
        )
        analysis.recommendations = self.recommend(ctx, financial, analysis)
        return analysis

    def recommend(
        self,
        ctx: IntelligenceDataContext,
        financial: dict[str, Any],
        analysis: CapabilityResult,
    ) -> list[CFORecommendation]:
        recs: list[CFORecommendation] = []
        for item in analysis.items:
            if item["type"] == "expense_outpacing_revenue":
                recs.append(CFORecommendation(
                    capability=self.capability_type,
                    title="Review expense categories",
                    description="Expenses are growing faster than revenue. Identify top cost drivers and negotiate vendor terms.",
                    rationale=item["message"],
                    priority=RecommendationPriority.HIGH,
                    confidence=87.0,
                    suggested_action="review_expenses",
                    data_sources=["accounting_twin", "vendor_intelligence"],
                ))
            elif item["type"] == "payables_pressure":
                recs.append(CFORecommendation(
                    capability=self.capability_type,
                    title="Prioritize receivable collection",
                    description="Outstanding payables exceed receivables. Accelerate collections before payment runs.",
                    rationale=item["message"],
                    priority=RecommendationPriority.HIGH,
                    confidence=85.0,
                    suggested_action="accelerate_collections",
                    impact_estimate={"cash_impact": "positive"},
                    data_sources=["outstanding", "financial_intelligence"],
                ))
        return recs
