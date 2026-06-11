"""Executive intelligence — C-level dashboard aggregation."""

from __future__ import annotations

from typing import Any

from backend.intelligence.analytics.data_source import IntelligenceDataContext
from backend.intelligence.customers.intelligence import CustomerIntelligence
from backend.intelligence.financial.intelligence import FinancialIntelligence
from backend.intelligence.gst.intelligence import GSTIntelligenceModule
from backend.intelligence.vendors.intelligence import VendorIntelligence


class ExecutiveIntelligence:
    def __init__(self):
        self.financial = FinancialIntelligence()
        self.gst = GSTIntelligenceModule()
        self.vendors = VendorIntelligence()
        self.customers = CustomerIntelligence()

    def analyze(self, ctx: IntelligenceDataContext, workflow_data: dict[str, Any], health_score: dict[str, Any]) -> dict[str, Any]:
        financial = self.financial.analyze(ctx)
        gst = self.gst.analyze(ctx)
        vendor_data = self.vendors.analyze(ctx)
        customer_data = self.customers.analyze(ctx)

        return {
            "revenue": financial["summary"]["revenue"],
            "expenses": financial["summary"]["expenses"],
            "profit": financial["summary"]["profit"],
            "profit_margin_pct": financial["summary"]["profit_margin_pct"],
            "gst_liability": gst["liability"]["net_liability"],
            "gst_output_tax": gst["liability"]["output_tax"]["total"],
            "gst_input_tax": gst["liability"]["input_tax"]["total"],
            "top_customers": customer_data["top_customers"][:5],
            "top_vendors": vendor_data["top_vendors"][:5],
            "pending_approvals": ctx.pending_approvals,
            "business_health_score": health_score,
            "cash_position": financial["summary"]["cash_position"],
            "receivables": financial["summary"]["receivables"],
            "payables": financial["summary"]["payables"],
            "charts": {
                "revenue_trend": financial["trends"]["revenue"],
                "expense_trend": financial["trends"]["expenses"],
                "gst_trend": gst["trends"]["net_liability"],
                "vendor_distribution": vendor_data["top_vendors"][:8],
                "customer_distribution": customer_data["top_customers"][:8],
                "workflow_statistics": workflow_data.get("execution_trends", []),
            },
            "growth": financial["growth"],
            "data_quality": {
                "avg_quality_score": ctx.avg_quality_score,
                "open_issues": ctx.open_data_issues,
                "voucher_count": len(ctx.all_vouchers),
            },
        }
