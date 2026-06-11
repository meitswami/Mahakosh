"""CFO Service — CEO Mode briefing and AI CFO orchestration."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.cfo.approval_gate import CFOApprovalGate
from backend.cfo.briefing.synthesizer import CEOBriefingSynthesizer
from backend.cfo.capabilities import ALL_CAPABILITIES
from backend.cfo.types import CFORecommendation
from backend.intelligence.analytics.anomaly_detector import AnomalyDetector
from backend.intelligence.analytics.data_source import IntelligenceDataContext
from backend.intelligence.analytics.insights_engine import InsightsEngine
from backend.intelligence.executive.health_score import BusinessHealthScorer
from backend.intelligence.executive.intelligence import ExecutiveIntelligence
from backend.intelligence.financial.intelligence import FinancialIntelligence
from backend.intelligence.workflows.intelligence import WorkflowIntelligence
from backend.models.cfo import CFOBriefingRecord


class CFOService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.briefing = CEOBriefingSynthesizer(db)
        self.approval_gate = CFOApprovalGate(db)
        self.anomaly_detector = AnomalyDetector()
        self.insights_engine = InsightsEngine()

    async def get_ceo_briefing(self, tenant_id: UUID, user_id: UUID, days: int = 30) -> dict[str, Any]:
        ctx = await IntelligenceDataContext(tenant_id, self.db).load()
        workflow = await WorkflowIntelligence(self.db).analyze(tenant_id, days)
        financial = FinancialIntelligence().analyze(ctx)
        health = BusinessHealthScorer().score(ctx, financial, workflow)
        executive = ExecutiveIntelligence().analyze(ctx, workflow, health)

        from backend.intelligence.gst.intelligence import GSTIntelligenceModule
        from backend.intelligence.vendors.intelligence import VendorIntelligence
        from backend.intelligence.customers.intelligence import CustomerIntelligence

        gst = GSTIntelligenceModule().analyze(ctx)
        vendors = VendorIntelligence().analyze(ctx)
        customers = CustomerIntelligence().analyze(ctx)
        insights = self.insights_engine.generate(ctx, financial, gst, vendors, customers, workflow, health)
        anomalies = self.anomaly_detector.detect(ctx)

        capabilities, all_recs = await self._run_capabilities(tenant_id, ctx, financial, workflow, health)

        stored_recs = []
        for rec in all_recs:
            if rec.requires_approval:
                record = await self.approval_gate.submit(tenant_id, user_id, rec)
                stored_recs.append(self.approval_gate._to_dict(record))
            else:
                stored_recs.append(rec.to_dict())

        briefing = await self.briefing.synthesize(
            tenant_id, ctx, executive, financial, workflow, health,
            insights, anomalies, capabilities, stored_recs,
        )

        self.db.add(CFOBriefingRecord(
            tenant_id=tenant_id,
            headline=briefing["headline"],
            health_score=health.get("score", 0),
            briefing_data=briefing,
            generated_for=user_id,
        ))
        await self.db.flush()

        return briefing

    async def _run_capabilities(
        self,
        tenant_id: UUID,
        ctx: IntelligenceDataContext,
        financial: dict[str, Any],
        workflow: dict[str, Any],
        health: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[CFORecommendation]]:
        capability_results: list[dict[str, Any]] = []
        all_recommendations: list[CFORecommendation] = []

        for cap_cls in ALL_CAPABILITIES:
            cap = cap_cls(self.db)
            result = await cap.analyze(tenant_id, ctx, financial, workflow, health)
            capability_results.append(result.to_dict())
            all_recommendations.extend(result.recommendations)

        all_recommendations.sort(
            key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r.priority.value, 4)
        )
        return capability_results, all_recommendations

    async def list_capabilities(self) -> list[dict[str, str]]:
        return [
            {
                "type": cap.capability_type.value,
                "name": cap.capability_type.value.replace("_", " ").title(),
                "requires_approval": "true",
                "auto_execute": "false",
                "status": "active",
            }
            for cap in ALL_CAPABILITIES
        ]

    async def list_recommendations(self, tenant_id: UUID) -> list[dict[str, Any]]:
        return await self.approval_gate.list_pending(tenant_id)

    async def approve_recommendation(
        self,
        tenant_id: UUID,
        recommendation_id: UUID,
        reviewer_id: UUID,
        notes: str | None = None,
    ) -> dict[str, Any]:
        return await self.approval_gate.approve(tenant_id, recommendation_id, reviewer_id, notes)

    async def reject_recommendation(
        self,
        tenant_id: UUID,
        recommendation_id: UUID,
        reviewer_id: UUID,
        notes: str | None = None,
    ) -> dict[str, Any]:
        return await self.approval_gate.reject(tenant_id, recommendation_id, reviewer_id, notes)
