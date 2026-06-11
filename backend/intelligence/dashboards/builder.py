"""Dashboard builders for each intelligence domain."""

from __future__ import annotations

from typing import Any

from backend.intelligence.analytics.data_source import IntelligenceDataContext
from backend.intelligence.customers.intelligence import CustomerIntelligence
from backend.intelligence.executive.health_score import BusinessHealthScorer
from backend.intelligence.executive.intelligence import ExecutiveIntelligence
from backend.intelligence.financial.intelligence import FinancialIntelligence
from backend.intelligence.gst.intelligence import GSTIntelligenceModule
from backend.intelligence.inventory.intelligence import InventoryIntelligence
from backend.intelligence.vendors.intelligence import VendorIntelligence


class DashboardBuilder:
  def build_accounting(self, ctx: IntelligenceDataContext) -> dict[str, Any]:
      financial = FinancialIntelligence().analyze(ctx)
      return {
          "type": "accounting",
          "summary": financial["summary"],
          "charts": {
              "revenue_trend": financial["trends"]["revenue"],
              "expense_trend": financial["trends"]["expenses"],
              "profit_trend": financial["trends"]["profit"],
          },
          "outstanding": financial["outstanding_analysis"],
          "health_metrics": financial["health_metrics"],
      }

  def build_gst(self, ctx: IntelligenceDataContext) -> dict[str, Any]:
      gst = GSTIntelligenceModule().analyze(ctx)
      return {
          "type": "gst",
          "liability": gst["liability"],
          "charts": gst["trends"],
          "anomalies": gst["anomalies"][:10],
      }

  def build_inventory(self, ctx: IntelligenceDataContext) -> dict[str, Any]:
      inv = InventoryIntelligence().analyze(ctx)
      return {"type": "inventory", **inv}

  def build_executive(
      self,
      ctx: IntelligenceDataContext,
      workflow: dict[str, Any],
  ) -> dict[str, Any]:
      financial = FinancialIntelligence().analyze(ctx)
      health = BusinessHealthScorer().score(ctx, financial, workflow)
      return ExecutiveIntelligence().analyze(ctx, workflow, health)

  def build_vendor_customer(self, ctx: IntelligenceDataContext) -> dict[str, Any]:
      return {
          "vendors": VendorIntelligence().analyze(ctx),
          "customers": CustomerIntelligence().analyze(ctx),
      }
