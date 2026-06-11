"""Business health score — composite 0-100 metric."""

from __future__ import annotations

from typing import Any

from backend.intelligence.analytics.data_source import IntelligenceDataContext
from backend.intelligence.financial.intelligence import FinancialIntelligence
from backend.intelligence.gst.intelligence import GSTIntelligenceModule
from backend.intelligence.inventory.intelligence import InventoryIntelligence


class BusinessHealthScorer:
    WEIGHTS = {
        "revenue_growth": 0.20,
        "cash_position": 0.15,
        "outstanding_receivables": 0.15,
        "inventory_quality": 0.15,
        "compliance_status": 0.20,
        "workflow_efficiency": 0.15,
    }

    def score(
        self,
        ctx: IntelligenceDataContext,
        financial: dict[str, Any],
        workflow: dict[str, Any],
    ) -> dict[str, Any]:
        components = {
            "revenue_growth": self._revenue_growth_score(financial),
            "cash_position": self._cash_position_score(financial),
            "outstanding_receivables": self._receivables_score(financial),
            "inventory_quality": self._inventory_score(ctx),
            "compliance_status": self._compliance_score(ctx),
            "workflow_efficiency": self._workflow_score(workflow),
        }

        total = sum(components[k] * self.WEIGHTS[k] for k in components)
        overall = round(min(100, max(0, total)), 1)
        level = "excellent" if overall >= 80 else "good" if overall >= 60 else "fair" if overall >= 40 else "needs_attention"

        return {
            "score": overall,
            "level": level,
            "components": {k: round(v, 1) for k, v in components.items()},
            "weights": self.WEIGHTS,
        }

    def _revenue_growth_score(self, financial: dict) -> float:
        growth = financial.get("growth", {}).get("revenue_pct")
        if growth is None:
            return 50.0
        if growth >= 20:
            return 100.0
        if growth >= 10:
            return 85.0
        if growth >= 0:
            return 70.0
        if growth >= -10:
            return 45.0
        return 25.0

    def _cash_position_score(self, financial: dict) -> float:
        cash = financial.get("summary", {}).get("cash_position", 0)
        payables = financial.get("summary", {}).get("payables", 0)
        if cash <= 0 and payables > 0:
            return 20.0
        if payables > 0:
            ratio = cash / payables
            return min(100, round(ratio * 50, 1))
        return 80.0 if cash > 0 else 50.0

    def _receivables_score(self, financial: dict) -> float:
        receivables = financial.get("summary", {}).get("receivables", 0)
        revenue = financial.get("summary", {}).get("revenue", 0)
        if revenue <= 0:
            return 60.0
        ratio = receivables / revenue
        if ratio <= 0.15:
            return 100.0
        if ratio <= 0.30:
            return 75.0
        if ratio <= 0.50:
            return 50.0
        return 25.0

    def _inventory_score(self, ctx: IntelligenceDataContext) -> float:
        inv = InventoryIntelligence().analyze(ctx)
        summary = inv.get("summary", {})
        total = summary.get("total_items", 0)
        if total == 0:
            return 60.0
        dead = summary.get("dead_stock_count", 0)
        moving = summary.get("moving_items", 0)
        dead_ratio = dead / total
        move_ratio = moving / total
        score = 100 - dead_ratio * 60 + move_ratio * 20
        return min(100, max(20, round(score, 1)))

    def _compliance_score(self, ctx: IntelligenceDataContext) -> float:
        gst = GSTIntelligenceModule().analyze(ctx)
        anomaly_count = len(gst.get("anomalies", []))
        issue_penalty = min(50, ctx.open_data_issues * 5 + anomaly_count * 8)
        quality_bonus = ctx.avg_quality_score * 0.3 if ctx.avg_quality_score else 0
        return min(100, max(0, round(70 - issue_penalty + quality_bonus, 1)))

    def _workflow_score(self, workflow: dict) -> float:
        perf = workflow.get("performance", {})
        success = perf.get("success_rate_pct", 100)
        pending = workflow.get("approval_delays", {}).get("pending_count", 0)
        delay_penalty = min(30, pending * 5)
        return min(100, max(0, round(success * 0.8 - delay_penalty + 20, 1)))
