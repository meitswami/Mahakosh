"""Strategic business insights capability — growth, concentration, market signals."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from backend.cfo.capabilities.base import BaseCFOCapability
from backend.cfo.types import CFOCapabilityType, CFORecommendation, CapabilityResult, RecommendationPriority
from backend.intelligence.analytics.data_source import IntelligenceDataContext
from backend.intelligence.customers.intelligence import CustomerIntelligence
from backend.intelligence.vendors.intelligence import VendorIntelligence


class StrategicInsightsCapability(BaseCFOCapability):
    capability_type = CFOCapabilityType.STRATEGIC_INSIGHTS

    async def analyze(
        self,
        tenant_id: UUID,
        ctx: IntelligenceDataContext,
        financial: dict[str, Any],
        workflow: dict[str, Any],
        health: dict[str, Any],
    ) -> CapabilityResult:
        vendors = VendorIntelligence().analyze(ctx)
        customers = CustomerIntelligence().analyze(ctx)
        growth = financial.get("growth", {})
        health_score = health.get("score", 0)

        items = []
        conc = vendors.get("concentration_risk", {})
        if conc.get("level") == "high":
            items.append({
                "type": "vendor_concentration",
                "message": conc.get("message", "High vendor concentration"),
                "severity": "medium",
            })

        risky = [c for c in customers.get("risk_scores", []) if c["risk_level"] == "high"]
        if risky:
            items.append({
                "type": "customer_risk",
                "message": f"{len(risky)} high-risk customers with significant outstanding",
                "severity": "high",
                "customers": [c["customer"] for c in risky[:3]],
            })

        rev_growth = growth.get("revenue_pct")
        if rev_growth is not None and rev_growth > 15:
            items.append({
                "type": "growth_opportunity",
                "message": f"Revenue growing {rev_growth}% — consider capacity expansion",
                "severity": "low",
            })

        analysis = CapabilityResult(
            capability=self.capability_type,
            status="insights_available",
            summary=f"Business health {health_score}/100 · {len(items)} strategic signals",
            items=items,
            metrics={
                "health_score": health_score,
                "revenue_growth_pct": rev_growth,
                "top_customer_concentration": customers.get("revenue_contribution", {}).get("top5_share_pct"),
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
            if item["type"] == "vendor_concentration":
                recs.append(CFORecommendation(
                    capability=self.capability_type,
                    title="Diversify supplier base",
                    description="Reduce dependency on top vendors to mitigate supply chain risk.",
                    rationale=item["message"],
                    priority=RecommendationPriority.MEDIUM,
                    confidence=80.0,
                    suggested_action="diversify_vendors",
                    requires_approval=True,
                    data_sources=["vendor_intelligence"],
                ))
            elif item["type"] == "customer_risk":
                recs.append(CFORecommendation(
                    capability=self.capability_type,
                    title="Review credit terms for at-risk customers",
                    description="High-risk customers may impact cash flow. Tighten credit policies.",
                    rationale=item["message"],
                    priority=RecommendationPriority.HIGH,
                    confidence=86.0,
                    suggested_action="review_credit_terms",
                    requires_approval=True,
                    data_sources=["customer_intelligence"],
                ))
        return recs
