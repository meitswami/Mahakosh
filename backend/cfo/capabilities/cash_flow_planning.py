"""Cash flow planning capability — projections and runway analysis."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from backend.cfo.capabilities.base import BaseCFOCapability
from backend.cfo.types import CFOCapabilityType, CFORecommendation, CapabilityResult, RecommendationPriority
from backend.intelligence.analytics.data_source import IntelligenceDataContext
from backend.intelligence.forecasting.engine import ForecastingEngine


class CashFlowPlanningCapability(BaseCFOCapability):
    capability_type = CFOCapabilityType.CASH_FLOW_PLANNING

    async def analyze(
        self,
        tenant_id: UUID,
        ctx: IntelligenceDataContext,
        financial: dict[str, Any],
        workflow: dict[str, Any],
        health: dict[str, Any],
    ) -> CapabilityResult:
        forecast = ForecastingEngine().forecast(ctx)
        cash_forecast = forecast.get("cash_flow", {})
        summary = financial.get("summary", {})
        current_cash = summary.get("cash_position", 0)
        receivables = summary.get("receivables", 0)
        payables = summary.get("payables", 0)

        projections = cash_forecast.get("projections", [])
        runway_months = None
        if projections and current_cash > 0:
            monthly_burn = abs(projections[0].get("projected_cash", current_cash) - current_cash) or 1
            if monthly_burn > 0:
                runway_months = round(current_cash / monthly_burn, 1)

        items = []
        if current_cash < payables * 0.5 and payables > 0:
            items.append({
                "type": "cash_shortfall_risk",
                "message": f"Cash (₹{current_cash:,.0f}) may not cover payables (₹{payables:,.0f})",
                "severity": "critical",
            })

        analysis = CapabilityResult(
            capability=self.capability_type,
            status="active" if items else "stable",
            summary=f"Cash position ₹{current_cash:,.0f} · Receivables ₹{receivables:,.0f}",
            items=items,
            metrics={
                "current_cash": current_cash,
                "receivables": receivables,
                "payables": payables,
                "runway_months": runway_months,
                "projections": projections,
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
            if item["type"] == "cash_shortfall_risk":
                recs.append(CFORecommendation(
                    capability=self.capability_type,
                    title="Create 30-day cash flow plan",
                    description="Current cash may not cover upcoming payables. Build a prioritized payment schedule.",
                    rationale=item["message"],
                    priority=RecommendationPriority.CRITICAL,
                    confidence=90.0,
                    suggested_action="create_cash_plan",
                    requires_approval=True,
                    data_sources=["cash_flow_forecast", "outstanding"],
                ))
        return recs
