"""CEO briefing synthesizer — answers the four questions every business owner needs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cfo.types import BriefingItem, BriefingSection, RecommendationPriority
from backend.intelligence.analytics.data_source import IntelligenceDataContext
from backend.intelligence.analytics.operational import OperationalIntelligence
from backend.models.workflow import Workflow


class CEOBriefingSynthesizer:
    """
    Synthesizes a CEO-ready briefing without requiring accounting reports.

    Four questions:
    1. What happened?     — completed events, closed periods, finished workflows
    2. What is happening? — live operations, running workflows, in-progress sync
    3. What needs attention? — approvals, anomalies, compliance, risks
    4. What should be done next? — prioritized CFO recommendations
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def synthesize(
        self,
        tenant_id: UUID,
        ctx: IntelligenceDataContext,
        executive: dict[str, Any],
        financial: dict[str, Any],
        workflow: dict[str, Any],
        health: dict[str, Any],
        insights: dict[str, Any],
        anomalies: list[dict[str, Any]],
        capabilities: list[dict[str, Any]],
        cfo_recommendations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        what_happened = await self._what_happened(tenant_id, ctx, executive, financial, workflow)
        what_is_happening = await self._what_is_happening(tenant_id, workflow)
        needs_attention = self._needs_attention(ctx, executive, anomalies, insights, workflow)
        next_actions = self._next_actions(cfo_recommendations, insights)

        attention_count = len(needs_attention)
        health_score = health.get("score", 0)
        health_level = health.get("level", "fair")

        headline = self._build_headline(health_score, health_level, attention_count, executive)

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "headline": headline,
            "health_score": health,
            "key_metrics": {
                "revenue": executive.get("revenue", 0),
                "expenses": executive.get("expenses", 0),
                "profit": executive.get("profit", 0),
                "profit_margin_pct": executive.get("profit_margin_pct", 0),
                "gst_liability": executive.get("gst_liability", 0),
                "cash_position": financial.get("summary", {}).get("cash_position", 0),
                "receivables": financial.get("summary", {}).get("receivables", 0),
                "payables": financial.get("summary", {}).get("payables", 0),
                "pending_approvals": executive.get("pending_approvals", 0),
            },
            "what_happened": [i.to_dict() for i in what_happened],
            "what_is_happening": [i.to_dict() for i in what_is_happening],
            "needs_attention": [i.to_dict() for i in needs_attention],
            "next_actions": [i.to_dict() for i in next_actions],
            "cfo_capabilities": capabilities,
            "growth": executive.get("growth", {}),
        }

    def _build_headline(
        self,
        score: float,
        level: str,
        attention_count: int,
        executive: dict,
    ) -> str:
        profit = executive.get("profit", 0)
        if attention_count == 0:
            return f"Business health {score:.0f}/100 ({level}) — all clear. Profit ₹{profit:,.0f}."
        if attention_count == 1:
            return f"Business health {score:.0f}/100 — 1 item needs your attention."
        return f"Business health {score:.0f}/100 — {attention_count} items need your attention."

    async def _what_happened(
        self,
        tenant_id: UUID,
        ctx: IntelligenceDataContext,
        executive: dict,
        financial: dict,
        workflow: dict,
    ) -> list[BriefingItem]:
        items: list[BriefingItem] = []

        completed = workflow.get("performance", {}).get("completed", 0)
        if completed > 0:
            items.append(BriefingItem(
                title=f"{completed} workflows completed",
                summary=f"Success rate {workflow.get('performance', {}).get('success_rate_pct', 0)}% in the last 30 days",
                section=BriefingSection.WHAT_HAPPENED,
                category="workflows",
                action_url="/workflows",
            ))

        rev_growth = financial.get("growth", {}).get("revenue_pct")
        revenue = executive.get("revenue", 0)
        if rev_growth is not None:
            direction = "increased" if rev_growth >= 0 else "decreased"
            items.append(BriefingItem(
                title=f"Revenue {direction} {abs(rev_growth):.1f}%",
                summary=f"Total revenue ₹{revenue:,.0f} across {len(ctx.sales_vouchers)} sales vouchers",
                section=BriefingSection.WHAT_HAPPENED,
                category="financial",
                confidence=90.0,
                action_url="/intelligence",
            ))

        operational = await OperationalIntelligence(self.db).analyze(tenant_id, 7)
        if operational.get("ocr_completed", 0) > 0:
            items.append(BriefingItem(
                title=f"{operational['ocr_completed']} documents processed",
                summary=f"OCR success rate {operational.get('ocr_success_rate_pct', 0)}% this week",
                section=BriefingSection.WHAT_HAPPENED,
                category="operations",
                action_url="/ocr",
            ))

        if operational.get("sync_completed", 0) > 0:
            items.append(BriefingItem(
                title=f"{operational['sync_completed']} accounting syncs completed",
                summary="Tally/accounting data updated in digital twin",
                section=BriefingSection.WHAT_HAPPENED,
                category="accounting",
                action_url="/accounting",
            ))

        since = datetime.now(UTC) - timedelta(days=7)
        wf_result = await self.db.execute(
            select(Workflow)
            .where(
                Workflow.tenant_id == tenant_id,
                Workflow.status == "completed",
                Workflow.completed_at >= since,
            )
            .order_by(Workflow.completed_at.desc())
            .limit(5)
        )
        for wf in wf_result.scalars().all():
            items.append(BriefingItem(
                title=wf.name,
                summary=f"{wf.workflow_type.replace('_', ' ').title()} completed",
                section=BriefingSection.WHAT_HAPPENED,
                category="workflow",
                entity_type="workflow",
                entity_id=str(wf.id),
                action_url=f"/workflows/{wf.id}",
                timestamp=wf.completed_at.isoformat() if wf.completed_at else "",
            ))

        if not items:
            items.append(BriefingItem(
                title="No recent activity recorded",
                summary="Sync accounting data or upload documents to see what happened",
                section=BriefingSection.WHAT_HAPPENED,
                category="system",
                priority=RecommendationPriority.LOW,
            ))

        return items[:12]

    async def _what_is_happening(
        self,
        tenant_id: UUID,
        workflow: dict,
    ) -> list[BriefingItem]:
        items: list[BriefingItem] = []

        live_result = await self.db.execute(
            select(Workflow)
            .where(
                Workflow.tenant_id == tenant_id,
                Workflow.status.in_(["running", "queued", "waiting", "paused"]),
            )
            .order_by(Workflow.started_at.desc().nullslast())
            .limit(8)
        )
        for wf in live_result.scalars().all():
            items.append(BriefingItem(
                title=wf.name,
                summary=f"{wf.workflow_type.replace('_', ' ').title()} — {wf.status}",
                section=BriefingSection.WHAT_IS_HAPPENING,
                category="workflow",
                priority=RecommendationPriority.MEDIUM,
                entity_type="workflow",
                entity_id=str(wf.id),
                action_url=f"/workflows/{wf.id}",
            ))

        active_agents = workflow.get("performance", {}).get("active_agents", 0)
        if active_agents > 0:
            items.append(BriefingItem(
                title=f"{active_agents} agents active",
                summary="Agent swarm processing tasks",
                section=BriefingSection.WHAT_IS_HAPPENING,
                category="agents",
                action_url="/agents",
            ))

        if not items:
            items.append(BriefingItem(
                title="Operations are quiet",
                summary="No workflows running. Mahakosh is ready for your next request.",
                section=BriefingSection.WHAT_IS_HAPPENING,
                category="system",
                priority=RecommendationPriority.LOW,
            ))

        return items

    def _needs_attention(
        self,
        ctx: IntelligenceDataContext,
        executive: dict,
        anomalies: list[dict],
        insights: dict,
        workflow: dict,
    ) -> list[BriefingItem]:
        items: list[BriefingItem] = []

        pending = executive.get("pending_approvals", 0)
        if pending > 0:
            items.append(BriefingItem(
                title=f"{pending} approvals waiting",
                summary="Workflow and accounting actions need your sign-off",
                section=BriefingSection.NEEDS_ATTENTION,
                category="approvals",
                priority=RecommendationPriority.HIGH,
                action_url="/workflows",
            ))

        for warning in insights.get("warnings", [])[:5]:
            items.append(BriefingItem(
                title=warning.get("text", "Warning")[:80],
                summary=warning.get("text", ""),
                section=BriefingSection.NEEDS_ATTENTION,
                category="insight",
                priority=RecommendationPriority.HIGH if warning.get("severity") in ("critical", "high") else RecommendationPriority.MEDIUM,
                confidence=warning.get("confidence", 80),
            ))

        for anomaly in anomalies[:5]:
            items.append(BriefingItem(
                title=anomaly.get("title", anomaly.get("type", "Anomaly")),
                summary=anomaly.get("description", anomaly.get("message", "")),
                section=BriefingSection.NEEDS_ATTENTION,
                category="anomaly",
                priority=RecommendationPriority.CRITICAL if anomaly.get("severity") == "critical" else RecommendationPriority.HIGH,
                confidence=90.0,
            ))

        approval_delays = workflow.get("approval_delays", {})
        if approval_delays.get("avg_pending_hours", 0) > 24:
            items.append(BriefingItem(
                title="Approval delays detected",
                summary=f"Average wait {approval_delays['avg_pending_hours']:.0f} hours",
                section=BriefingSection.NEEDS_ATTENTION,
                category="workflows",
                priority=RecommendationPriority.MEDIUM,
                action_url="/workflows",
            ))

        if ctx.open_data_issues > 5:
            items.append(BriefingItem(
                title=f"{ctx.open_data_issues} data quality issues",
                summary="Accounting twin has open issues affecting report accuracy",
                section=BriefingSection.NEEDS_ATTENTION,
                category="data_quality",
                priority=RecommendationPriority.MEDIUM,
                action_url="/accounting",
            ))

        gst_liability = executive.get("gst_liability", 0)
        if gst_liability > 50000:
            items.append(BriefingItem(
                title=f"GST liability ₹{gst_liability:,.0f}",
                summary="Review GST position before filing deadline",
                section=BriefingSection.NEEDS_ATTENTION,
                category="compliance",
                priority=RecommendationPriority.MEDIUM,
                action_url="/intelligence",
            ))

        return sorted(items, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.priority.value, 4))

    def _next_actions(
        self,
        cfo_recommendations: list[dict],
        insights: dict,
    ) -> list[BriefingItem]:
        items: list[BriefingItem] = []

        for rec in cfo_recommendations[:8]:
            items.append(BriefingItem(
                title=rec.get("title", "Recommendation"),
                summary=rec.get("description", rec.get("rationale", "")),
                section=BriefingSection.NEXT_ACTIONS,
                category=rec.get("capability", "cfo"),
                priority=RecommendationPriority(rec.get("priority", "medium")),
                confidence=rec.get("confidence", 80),
                metadata={
                    "requires_approval": rec.get("requires_approval", True),
                    "suggested_action": rec.get("suggested_action"),
                    "recommendation_id": rec.get("id"),
                },
                action_url="/ceo",
            ))

        for rec in insights.get("recommendations", [])[:3]:
            if len(items) >= 10:
                break
            items.append(BriefingItem(
                title=rec.get("text", "Recommendation")[:80],
                summary=rec.get("text", ""),
                section=BriefingSection.NEXT_ACTIONS,
                category="insight",
                priority=RecommendationPriority.MEDIUM,
                confidence=rec.get("confidence", 75),
                metadata={"action": rec.get("action"), "requires_approval": True},
            ))

        if not items:
            items.append(BriefingItem(
                title="Sync your accounting data",
                summary="Connect Tally or import vouchers to unlock AI CFO recommendations",
                section=BriefingSection.NEXT_ACTIONS,
                category="onboarding",
                priority=RecommendationPriority.MEDIUM,
                action_url="/accounting",
            ))

        return items
