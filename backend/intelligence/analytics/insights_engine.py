"""AI insights engine — observations, recommendations, warnings, opportunities."""

from __future__ import annotations

from typing import Any

from backend.intelligence.analytics.data_source import IntelligenceDataContext
from backend.intelligence.customers.intelligence import CustomerIntelligence
from backend.intelligence.executive.health_score import BusinessHealthScorer
from backend.intelligence.financial.intelligence import FinancialIntelligence
from backend.intelligence.gst.intelligence import GSTIntelligenceModule
from backend.intelligence.vendors.intelligence import VendorIntelligence


class InsightsEngine:
    """Generate structured insights and answer natural language analytics questions."""

    def generate(
        self,
        ctx: IntelligenceDataContext,
        financial: dict[str, Any],
        gst: dict[str, Any],
        vendors: dict[str, Any],
        customers: dict[str, Any],
        workflow: dict[str, Any],
        health: dict[str, Any],
    ) -> dict[str, Any]:
        observations = self._observations(financial, gst, vendors, customers, workflow, health)
        recommendations = self._recommendations(financial, gst, vendors, customers, workflow, health)
        warnings = self._warnings(gst, vendors, customers, workflow, health)
        opportunities = self._opportunities(financial, customers, vendors)

        return {
            "observations": observations,
            "recommendations": recommendations,
            "warnings": warnings,
            "opportunities": opportunities,
        }

    def answer_question(
        self,
        question: str,
        ctx: IntelligenceDataContext,
        financial: dict[str, Any],
        gst: dict[str, Any],
        vendors: dict[str, Any],
        customers: dict[str, Any],
        workflow: dict[str, Any],
        health: dict[str, Any],
    ) -> dict[str, Any]:
        q = question.lower().strip()
        answer = ""
        confidence = 75.0
        insight_type = "observation"

        if any(kw in q for kw in ("expense", "spending", "cost")):
            growth = financial.get("growth", {}).get("expense_pct")
            total = financial["summary"]["expenses"]
            if growth is not None and growth > 10:
                answer = (
                    f"Expenses increased {growth:.1f}% in the latest period to ₹{total:,.0f}. "
                    f"Top vendor {vendors['top_vendors'][0]['name'] if vendors.get('top_vendors') else 'N/A'} "
                    f"accounts for significant purchase volume."
                )
                insight_type = "recommendation"
                confidence = 88.0
            else:
                answer = f"Total expenses are ₹{total:,.0f}. " + (
                    f"Expense growth is {growth:.1f}% period-over-period." if growth is not None else "Insufficient period data for trend."
                )
                confidence = 82.0

        elif any(kw in q for kw in ("vendor", "supplier", "purchase")):
            top = vendors.get("top_vendors", [])
            if "fastest" in q or "grow" in q:
                trends = vendors.get("purchase_trends", [])
                if len(trends) >= 2:
                    answer = f"Purchase volume trend shows {trends[-1]['value']:,.0f} in {trends[-1]['label']} vs {trends[-2]['value']:,.0f} previously."
                    confidence = 85.0
                else:
                    answer = f"Top vendor by purchase value: {top[0]['name']} (₹{top[0]['value']:,.0f}, {top[0]['share_pct']}% share)." if top else "No vendor purchase data available."
            else:
                conc = vendors.get("concentration_risk", {})
                answer = conc.get("message", "No vendor data") + (
                    f" Top vendor: {top[0]['name']}." if top else ""
                )
                confidence = 90.0

        elif any(kw in q for kw in ("gst", "tax", "liability", "itc")):
            liability = gst["liability"]["net_liability"]
            anomalies = len(gst.get("anomalies", []))
            answer = (
                f"Net GST liability is ₹{liability:,.0f}. "
                f"Output tax: ₹{gst['liability']['output_tax']['total']:,.0f}, "
                f"Input tax credit: ₹{gst['liability']['input_tax']['total']:,.0f}."
            )
            if anomalies:
                answer += f" {anomalies} GST anomalies detected requiring review."
                insight_type = "warning"
                confidence = 92.0
            else:
                confidence = 94.0

        elif any(kw in q for kw in ("customer", "receivable", "risky", "risk")):
            risky = [c for c in customers.get("risk_scores", []) if c["risk_level"] in ("high", "medium")]
            if risky:
                names = ", ".join(c["customer"] for c in risky[:3])
                answer = f"{len(risky)} customers flagged for risk. Highest concern: {names}. Total receivables: ₹{customers.get('total_receivables', 0):,.0f}."
                insight_type = "warning"
                confidence = 89.0
            else:
                answer = f"No high-risk customers identified. Total receivables: ₹{customers.get('total_receivables', 0):,.0f}."
                confidence = 86.0

        elif any(kw in q for kw in ("health", "score", "overall")):
            answer = f"Business health score is {health['score']}/100 ({health['level']}). Weakest area: {min(health['components'], key=health['components'].get)}."
            confidence = 91.0

        elif any(kw in q for kw in ("revenue", "sales", "profit")):
            s = financial["summary"]
            growth = financial.get("growth", {}).get("revenue_pct")
            answer = f"Revenue: ₹{s['revenue']:,.0f}, Profit: ₹{s['profit']:,.0f} ({s['profit_margin_pct']}% margin)."
            if growth is not None:
                answer += f" Revenue growth: {growth:.1f}%."
            confidence = 93.0

        elif any(kw in q for kw in ("workflow", "approval", "delay")):
            perf = workflow.get("performance", {})
            delays = workflow.get("approval_delays", {})
            answer = (
                f"Workflow success rate: {perf.get('success_rate_pct', 0)}%. "
                f"{delays.get('pending_count', 0)} pending approvals, avg wait {delays.get('avg_pending_hours', 0)} hours."
            )
            confidence = 87.0

        else:
            insights = self.generate(ctx, financial, gst, vendors, customers, workflow, health)
            top_obs = insights["observations"][0] if insights["observations"] else None
            if top_obs:
                answer = top_obs["text"]
                confidence = top_obs.get("confidence", 75)
                insight_type = top_obs["type"]
            else:
                answer = "Insufficient data to answer. Sync accounting data from Tally or upload vouchers to enable analytics."
                confidence = 50.0

        return {
            "question": question,
            "answer": answer,
            "type": insight_type,
            "confidence": confidence,
            "confidence_display": f"{confidence:.0f}%",
        }

    def _observations(self, financial, gst, vendors, customers, workflow, health) -> list[dict]:
        obs: list[dict] = []
        rev_growth = financial.get("growth", {}).get("revenue_pct")
        exp_growth = financial.get("growth", {}).get("expense_pct")
        if rev_growth is not None and rev_growth > 5:
            obs.append({"type": "observation", "text": f"Revenue grew {rev_growth:.1f}% in the latest period.", "confidence": 90})
        if exp_growth is not None and exp_growth > 10:
            obs.append({"type": "observation", "text": f"Expenses increased {exp_growth:.1f}% — review cost drivers.", "confidence": 88})
        liability = gst["liability"]["net_liability"]
        if liability > 0:
            obs.append({"type": "observation", "text": f"Net GST liability stands at ₹{liability:,.0f}.", "confidence": 94})
        obs.append({"type": "observation", "text": f"Business health score: {health['score']}/100 ({health['level']}).", "confidence": 91})
        return obs

    def _recommendations(self, financial, gst, vendors, customers, workflow, health) -> list[dict]:
        recs: list[dict] = []
        if gst.get("anomalies"):
            recs.append({
                "type": "recommendation",
                "text": "Review recent vendor purchases for GST compliance gaps.",
                "confidence": 92,
                "action": "review_gst_anomalies",
            })
        conc = vendors.get("concentration_risk", {})
        if conc.get("level") == "high":
            recs.append({
                "type": "recommendation",
                "text": f"Diversify vendor base — top 3 vendors are {conc['top3_share_pct']}% of purchases.",
                "confidence": 87,
                "action": "diversify_vendors",
            })
        risky = [c for c in customers.get("risk_scores", []) if c["risk_level"] == "high"]
        if risky:
            recs.append({
                "type": "recommendation",
                "text": f"Follow up on receivables from {risky[0]['customer']} (₹{risky[0]['outstanding']:,.0f} outstanding).",
                "confidence": 85,
                "action": "collect_receivables",
            })
        if workflow.get("approval_delays", {}).get("pending_count", 0) > 3:
            recs.append({
                "type": "recommendation",
                "text": "Clear pending approvals to avoid workflow bottlenecks.",
                "confidence": 83,
                "action": "clear_approvals",
            })
        return recs

    def _warnings(self, gst, vendors, customers, workflow, health) -> list[dict]:
        warnings: list[dict] = []
        for a in gst.get("anomalies", [])[:3]:
            warnings.append({"type": "warning", "text": a.get("message", "GST anomaly"), "confidence": 90, "severity": a.get("severity")})
        for c in customers.get("risk_scores", []):
            if c["risk_level"] == "high":
                warnings.append({
                    "type": "warning",
                    "text": f"High-risk customer: {c['customer']} — ₹{c['outstanding']:,.0f} outstanding",
                    "confidence": 86,
                    "severity": "high",
                })
        if health["score"] < 50:
            warnings.append({
                "type": "warning",
                "text": f"Business health score is critically low at {health['score']}/100.",
                "confidence": 95,
                "severity": "critical",
            })
        return warnings

    def _opportunities(self, financial, customers, vendors) -> list[dict]:
        opps: list[dict] = []
        margin = financial["summary"].get("profit_margin_pct", 0)
        if margin > 15:
            opps.append({
                "type": "opportunity",
                "text": f"Strong profit margin of {margin}% — consider reinvestment in growth.",
                "confidence": 80,
            })
        top_cust = customers.get("top_customers", [])
        if top_cust and top_cust[0].get("share_pct", 0) < 30:
            opps.append({
                "type": "opportunity",
                "text": "Healthy customer diversification — low concentration risk.",
                "confidence": 78,
            })
        return opps
