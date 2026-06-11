"""Compliance alerts capability — GST, data quality, regulatory risks."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from backend.cfo.capabilities.base import BaseCFOCapability
from backend.cfo.types import CFOCapabilityType, CFORecommendation, CapabilityResult, RecommendationPriority
from backend.intelligence.analytics.data_source import IntelligenceDataContext
from backend.intelligence.gst.intelligence import GSTIntelligenceModule


class ComplianceAlertsCapability(BaseCFOCapability):
    capability_type = CFOCapabilityType.COMPLIANCE_ALERTS

    async def analyze(
        self,
        tenant_id: UUID,
        ctx: IntelligenceDataContext,
        financial: dict[str, Any],
        workflow: dict[str, Any],
        health: dict[str, Any],
    ) -> CapabilityResult:
        gst = GSTIntelligenceModule().analyze(ctx)
        anomalies = gst.get("anomalies", [])
        open_issues = ctx.open_data_issues

        items = []
        for a in anomalies[:10]:
            items.append({
                "type": "gst_anomaly",
                "message": a.get("message", "GST issue detected"),
                "severity": a.get("severity", "medium"),
                "voucher_number": a.get("voucher_number"),
            })

        if open_issues > 0:
            items.append({
                "type": "data_quality",
                "message": f"{open_issues} open data quality issues in accounting twin",
                "severity": "medium" if open_issues < 10 else "high",
                "count": open_issues,
            })

        liability = gst.get("liability", {}).get("net_liability", 0)
        if liability > 100000:
            items.append({
                "type": "gst_liability",
                "message": f"Net GST liability ₹{liability:,.0f} — ensure filing readiness",
                "severity": "medium",
                "amount": liability,
            })

        analysis = CapabilityResult(
            capability=self.capability_type,
            status="alerts_active" if items else "compliant",
            summary=f"{len(items)} compliance items · GST liability ₹{liability:,.0f}",
            items=items,
            metrics={"gst_liability": liability, "anomaly_count": len(anomalies), "open_issues": open_issues},
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
        gst_anomalies = [i for i in analysis.items if i["type"] == "gst_anomaly"]
        if gst_anomalies:
            recs.append(CFORecommendation(
                capability=self.capability_type,
                title="Resolve GST compliance gaps",
                description=f"{len(gst_anomalies)} GST anomalies need review before filing.",
                rationale=gst_anomalies[0]["message"],
                priority=RecommendationPriority.HIGH,
                confidence=92.0,
                suggested_action="review_gst_anomalies",
                requires_approval=True,
                data_sources=["gst_intelligence", "accounting_twin"],
            ))
        if any(i["type"] == "data_quality" for i in analysis.items):
            recs.append(CFORecommendation(
                capability=self.capability_type,
                title="Run data quality cleanup",
                description="Open accounting data issues may affect compliance reports.",
                rationale="Data quality issues detected in digital twin",
                priority=RecommendationPriority.MEDIUM,
                confidence=85.0,
                suggested_action="run_data_cleanup",
                requires_approval=True,
                data_sources=["accounting_twin", "data_issues"],
            ))
        return recs
