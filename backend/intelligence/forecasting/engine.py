"""Forecasting engine — revenue, purchase, inventory, cash flow projections."""

from __future__ import annotations

from typing import Any

from backend.intelligence.analytics.aggregators import trend_series
from backend.intelligence.analytics.data_source import IntelligenceDataContext
from backend.intelligence.financial.intelligence import FinancialIntelligence
from backend.intelligence.inventory.intelligence import InventoryIntelligence


class ForecastingEngine:
    """Linear trend extrapolation from historical twin data."""

    def forecast(self, ctx: IntelligenceDataContext, periods_ahead: int = 3) -> dict[str, Any]:
        financial = FinancialIntelligence().analyze(ctx)
        inventory = InventoryIntelligence().analyze(ctx)

        return {
            "revenue": self._forecast_series(financial["trends"]["revenue"], periods_ahead, "revenue"),
            "purchases": self._forecast_series(
                [{"period": t["period"], "value": t["value"]} for t in financial["trends"]["expenses"]],
                periods_ahead,
                "purchases",
            ),
            "cash_flow": self._forecast_cash_flow(financial, periods_ahead),
            "inventory": {
                "current_valuation": inventory["summary"]["total_valuation"],
                "projected_demand": self._forecast_series(
                    [{"period": "current", "value": inventory["summary"]["total_valuation"]}],
                    periods_ahead,
                    "inventory_valuation",
                ),
                "methodology": "linear_extrapolation",
            },
            "methodology": "simple_linear_regression",
            "disclaimer": "Forecasts based on historical twin data. Accuracy improves with more synced periods.",
        }

    def _forecast_series(
        self,
        history: list[dict[str, Any]],
        periods_ahead: int,
        metric: str,
    ) -> dict[str, Any]:
        if len(history) < 2:
            return {
                "metric": metric,
                "historical": history,
                "forecast": [],
                "confidence": 40.0,
                "message": "Insufficient history for reliable forecast",
            }

        values = [h["value"] for h in history]
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        slope = sum((i - x_mean) * (values[i] - y_mean) for i in range(n)) / max(sum((i - x_mean) ** 2 for i in range(n)), 1)

        forecast = []
        for i in range(1, periods_ahead + 1):
            projected = round(values[-1] + slope * i, 2)
            forecast.append({"period_ahead": i, "projected_value": max(0, projected)})

        variance = sum((v - y_mean) ** 2 for v in values) / n
        confidence = min(95, max(50, 80 - variance / max(y_mean, 1) * 10))

        return {
            "metric": metric,
            "historical": history[-6:],
            "forecast": forecast,
            "trend_slope": round(slope, 2),
            "confidence": round(confidence, 1),
        }

    def _forecast_cash_flow(self, financial: dict, periods_ahead: int) -> dict[str, Any]:
        cash = financial["summary"]["cash_position"]
        receivables = financial["summary"]["receivables"]
        payables = financial["summary"]["payables"]
        net_monthly = financial["summary"]["profit"] / max(len(financial["trends"]["profit"]), 1)

        projections = []
        running = cash
        for i in range(1, periods_ahead + 1):
            running = round(running + net_monthly, 2)
            projections.append({
                "period_ahead": i,
                "projected_cash": running,
                "receivables_impact": round(receivables * 0.3 / periods_ahead, 2),
                "payables_impact": round(-payables * 0.2 / periods_ahead, 2),
            })

        return {
            "current_cash": cash,
            "projections": projections,
            "confidence": 65.0,
        }
