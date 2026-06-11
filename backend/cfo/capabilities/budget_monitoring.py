"""Budget monitoring capability — actual vs planned variance tracking."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from backend.cfo.capabilities.base import BaseCFOCapability
from backend.cfo.types import CFOCapabilityType, CFORecommendation, CapabilityResult, RecommendationPriority
from backend.intelligence.analytics.data_source import IntelligenceDataContext


class BudgetMonitoringCapability(BaseCFOCapability):
    capability_type = CFOCapabilityType.BUDGET_MONITORING

    async def analyze(
        self,
        tenant_id: UUID,
        ctx: IntelligenceDataContext,
        financial: dict[str, Any],
        workflow: dict[str, Any],
        health: dict[str, Any],
    ) -> CapabilityResult:
        summary = financial.get("summary", {})
        revenue = summary.get("revenue", 0)
        expenses = summary.get("expenses", 0)
        trends = financial.get("trends", {})
        expense_trend = trends.get("expenses", [])

        items = []
        if len(expense_trend) >= 2:
            latest = expense_trend[-1]["value"]
            prior = expense_trend[-2]["value"]
            if prior > 0:
                variance_pct = round((latest - prior) / prior * 100, 1)
                if abs(variance_pct) > 15:
                    items.append({
                        "type": "expense_variance",
                        "message": f"Monthly expenses shifted {variance_pct:+.1f}% vs prior period",
                        "variance_pct": variance_pct,
                        "severity": "medium" if abs(variance_pct) < 25 else "high",
                    })

        expense_ratio = round(expenses / revenue * 100, 1) if revenue > 0 else None
        if expense_ratio and expense_ratio > 85:
            items.append({
                "type": "high_expense_ratio",
                "message": f"Expense-to-revenue ratio is {expense_ratio}%",
                "severity": "high",
            })

        analysis = CapabilityResult(
            capability=self.capability_type,
            status="variance_detected" if items else "on_track",
            summary=f"Expense ratio {expense_ratio}% of revenue" if expense_ratio else "Insufficient data for budget tracking",
            items=items,
            metrics={"expense_ratio_pct": expense_ratio, "revenue": revenue, "expenses": expenses},
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
            if item["type"] == "high_expense_ratio":
                recs.append(CFORecommendation(
                    capability=self.capability_type,
                    title="Set departmental spending caps",
                    description="Expenses exceed 85% of revenue. Review and cap discretionary spending.",
                    rationale=item["message"],
                    priority=RecommendationPriority.HIGH,
                    confidence=82.0,
                    suggested_action="set_spending_caps",
                    requires_approval=True,
                    data_sources=["financial_intelligence"],
                ))
        return recs
