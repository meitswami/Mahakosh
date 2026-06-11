"""Intelligence service — orchestrates all BI modules."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.intelligence.analytics.anomaly_detector import AnomalyDetector
from backend.intelligence.analytics.data_source import IntelligenceDataContext
from backend.intelligence.analytics.insights_engine import InsightsEngine
from backend.intelligence.analytics.operational import OperationalIntelligence
from backend.intelligence.customers.intelligence import CustomerIntelligence
from backend.intelligence.dashboards.builder import DashboardBuilder
from backend.intelligence.executive.health_score import BusinessHealthScorer
from backend.intelligence.executive.intelligence import ExecutiveIntelligence
from backend.intelligence.financial.intelligence import FinancialIntelligence
from backend.intelligence.forecasting.engine import ForecastingEngine
from backend.intelligence.gst.intelligence import GSTIntelligenceModule
from backend.intelligence.inventory.intelligence import InventoryIntelligence
from backend.intelligence.reporting.engine import ReportEngine
from backend.intelligence.vendors.intelligence import VendorIntelligence
from backend.intelligence.workflows.intelligence import WorkflowIntelligence
from backend.models.analytics import (
    AnalyticsSnapshot,
    AnomalyEvent,
    BusinessScore,
)


class IntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.report_engine = ReportEngine()
        self.insights_engine = InsightsEngine()
        self.anomaly_detector = AnomalyDetector()
        self.forecasting = ForecastingEngine()
        self.dashboards = DashboardBuilder()

    async def _load(self, tenant_id: UUID) -> IntelligenceDataContext:
        return await IntelligenceDataContext(tenant_id, self.db).load()

    async def get_financial(self, tenant_id: UUID) -> dict[str, Any]:
        ctx = await self._load(tenant_id)
        return FinancialIntelligence().analyze(ctx)

    async def get_gst(self, tenant_id: UUID) -> dict[str, Any]:
        ctx = await self._load(tenant_id)
        return GSTIntelligenceModule().analyze(ctx)

    async def get_vendors(self, tenant_id: UUID) -> dict[str, Any]:
        ctx = await self._load(tenant_id)
        return VendorIntelligence().analyze(ctx)

    async def get_customers(self, tenant_id: UUID) -> dict[str, Any]:
        ctx = await self._load(tenant_id)
        return CustomerIntelligence().analyze(ctx)

    async def get_inventory(self, tenant_id: UUID) -> dict[str, Any]:
        ctx = await self._load(tenant_id)
        return InventoryIntelligence().analyze(ctx)

    async def get_workflows(self, tenant_id: UUID, days: int = 30) -> dict[str, Any]:
        return await WorkflowIntelligence(self.db).analyze(tenant_id, days)

    async def get_executive(self, tenant_id: UUID, days: int = 30) -> dict[str, Any]:
        ctx = await self._load(tenant_id)
        workflow = await self.get_workflows(tenant_id, days)
        financial = FinancialIntelligence().analyze(ctx)
        health = BusinessHealthScorer().score(ctx, financial, workflow)
        executive = ExecutiveIntelligence().analyze(ctx, workflow, health)
        insights = await self._build_insights(ctx, workflow, health)
        anomalies = self.anomaly_detector.detect(ctx)
        await self._persist_snapshot(tenant_id, "executive", executive)
        await self._persist_score(tenant_id, health)
        await self._persist_anomalies(tenant_id, anomalies)
        return {
            **executive,
            "insights": insights,
            "anomalies": anomalies[:10],
            "operational": await OperationalIntelligence(self.db).analyze(tenant_id, days),
        }

    async def get_insights(self, tenant_id: UUID, days: int = 30) -> dict[str, Any]:
        ctx = await self._load(tenant_id)
        workflow = await self.get_workflows(tenant_id, days)
        financial = FinancialIntelligence().analyze(ctx)
        gst = GSTIntelligenceModule().analyze(ctx)
        vendors = VendorIntelligence().analyze(ctx)
        customers = CustomerIntelligence().analyze(ctx)
        health = BusinessHealthScorer().score(ctx, financial, workflow)
        return self.insights_engine.generate(ctx, financial, gst, vendors, customers, workflow, health)

    async def query(self, tenant_id: UUID, question: str, days: int = 30) -> dict[str, Any]:
        ctx = await self._load(tenant_id)
        workflow = await self.get_workflows(tenant_id, days)
        financial = FinancialIntelligence().analyze(ctx)
        gst = GSTIntelligenceModule().analyze(ctx)
        vendors = VendorIntelligence().analyze(ctx)
        customers = CustomerIntelligence().analyze(ctx)
        health = BusinessHealthScorer().score(ctx, financial, workflow)
        return self.insights_engine.answer_question(
            question, ctx, financial, gst, vendors, customers, workflow, health
        )

    async def get_forecasts(self, tenant_id: UUID) -> dict[str, Any]:
        ctx = await self._load(tenant_id)
        return self.forecasting.forecast(ctx)

    async def get_anomalies(self, tenant_id: UUID) -> list[dict[str, Any]]:
        ctx = await self._load(tenant_id)
        return self.anomaly_detector.detect(ctx)

    async def get_dashboard(self, dashboard_type: str, tenant_id: UUID, days: int = 30) -> dict[str, Any]:
        ctx = await self._load(tenant_id)
        if dashboard_type == "executive":
            workflow = await self.get_workflows(tenant_id, days)
            return self.dashboards.build_executive(ctx, workflow)
        if dashboard_type == "accounting":
            return self.dashboards.build_accounting(ctx)
        if dashboard_type == "gst":
            return self.dashboards.build_gst(ctx)
        if dashboard_type == "inventory":
            return self.dashboards.build_inventory(ctx)
        if dashboard_type == "workflow":
            return await self.get_workflows(tenant_id, days)
        raise ValueError(f"Unknown dashboard type: {dashboard_type}")

    async def generate_report(
        self,
        tenant_id: UUID,
        report_type: str,
        fmt: str = "excel",
        days: int = 30,
    ) -> tuple[bytes, str, str]:
        data: dict[str, Any] = {"report_type": report_type}
        if report_type == "gst_summary":
            data.update(await self.get_gst(tenant_id))
        elif report_type in ("vendor_ledger", "purchase_register"):
            data.update(await self.get_vendors(tenant_id))
        elif report_type in ("sales_register", "customer_report"):
            data.update(await self.get_customers(tenant_id))
        elif report_type == "executive_summary":
            data.update(await self.get_executive(tenant_id, days))
        elif report_type == "financial_summary":
            data.update(await self.get_financial(tenant_id))
        elif report_type == "workflow_report":
            data.update(await self.get_workflows(tenant_id, days))
        else:
            data.update(await self.get_executive(tenant_id, days))

        data["insights"] = await self.get_insights(tenant_id, days)
        return self.report_engine.generate(report_type, data, fmt)

    async def _build_insights(self, ctx, workflow, health) -> dict[str, Any]:
        financial = FinancialIntelligence().analyze(ctx)
        gst = GSTIntelligenceModule().analyze(ctx)
        vendors = VendorIntelligence().analyze(ctx)
        customers = CustomerIntelligence().analyze(ctx)
        return self.insights_engine.generate(ctx, financial, gst, vendors, customers, workflow, health)

    async def _persist_snapshot(self, tenant_id: UUID, snapshot_type: str, data: dict) -> None:
        self.db.add(AnalyticsSnapshot(
            tenant_id=tenant_id,
            snapshot_type=snapshot_type,
            snapshot_date=date.today(),
            data=data,
        ))
        await self.db.flush()

    async def _persist_score(self, tenant_id: UUID, health: dict) -> None:
        self.db.add(BusinessScore(
            tenant_id=tenant_id,
            score_date=date.today(),
            overall_score=health["score"],
            level=health["level"],
            components=health["components"],
        ))
        await self.db.flush()

    async def _persist_anomalies(self, tenant_id: UUID, anomalies: list[dict]) -> None:
        for a in anomalies[:20]:
            self.db.add(AnomalyEvent(
                tenant_id=tenant_id,
                event_type=a.get("type", "unknown"),
                severity=a.get("severity", "medium"),
                title=a.get("title", a.get("type", "Anomaly")),
                description=a.get("description", ""),
                entity_type=a.get("entity_type"),
                entity_id=a.get("entity_id"),
                payload=a,
                status="open",
            ))
        await self.db.flush()
