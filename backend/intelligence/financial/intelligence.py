"""Financial intelligence — profit, revenue, expense, cash flow, outstanding."""

from __future__ import annotations

from typing import Any

from backend.intelligence.analytics.aggregators import (
    apply_share_pct,
    group_by_month,
    growth_pct,
    parse_date,
    sum_field,
    top_n_by_field,
    trend_series,
)
from backend.intelligence.analytics.data_source import IntelligenceDataContext


class FinancialIntelligence:
    def analyze(self, ctx: IntelligenceDataContext) -> dict[str, Any]:
        sales = ctx.sales_vouchers
        purchases = ctx.purchase_vouchers

        revenue_total = sum_field(sales, "total_amount") or sum_field(sales, "subtotal")
        expense_total = sum_field(purchases, "total_amount") or sum_field(purchases, "subtotal")
        profit = round(revenue_total - expense_total, 2)
        profit_margin = round(profit / revenue_total * 100, 2) if revenue_total else 0.0

        revenue_trend = group_by_month(sales, "voucher_date", "total_amount")
        if not revenue_trend:
            revenue_trend = group_by_month(sales, "voucher_date", "subtotal")
        expense_trend = group_by_month(purchases, "voucher_date", "total_amount")
        if not expense_trend:
            expense_trend = group_by_month(purchases, "voucher_date", "subtotal")

        rev_keys = sorted(revenue_trend.keys())
        exp_keys = sorted(expense_trend.keys())
        recent_rev = revenue_trend.get(rev_keys[-1], 0) if rev_keys else 0
        prior_rev = revenue_trend.get(rev_keys[-2], 0) if len(rev_keys) > 1 else 0
        recent_exp = expense_trend.get(exp_keys[-1], 0) if exp_keys else 0
        prior_exp = expense_trend.get(exp_keys[-2], 0) if len(exp_keys) > 1 else 0

        receivable_total = sum_field(ctx.receivables, "amount")
        payable_total = sum_field(ctx.payables, "amount")
        cash_ledgers = [
            l for l in ctx.ledgers
            if (l.get("ledger_type") or "").lower() in ("bank", "cash")
            or "bank" in (l.get("name") or "").lower()
            or "cash" in (l.get("name") or "").lower()
        ]
        cash_position = sum_field(cash_ledgers, "current_balance")

        profit_trend: dict[str, float] = {}
        all_months = sorted(set(revenue_trend) | set(expense_trend))
        for m in all_months:
            profit_trend[m] = round(revenue_trend.get(m, 0) - expense_trend.get(m, 0), 2)

        return {
            "summary": {
                "revenue": revenue_total,
                "expenses": expense_total,
                "profit": profit,
                "profit_margin_pct": profit_margin,
                "cash_position": cash_position,
                "receivables": receivable_total,
                "payables": payable_total,
                "net_outstanding": round(receivable_total - payable_total, 2),
            },
            "trends": {
                "revenue": trend_series(revenue_trend),
                "expenses": trend_series(expense_trend),
                "profit": trend_series(profit_trend),
            },
            "growth": {
                "revenue_pct": growth_pct(recent_rev, prior_rev),
                "expense_pct": growth_pct(recent_exp, prior_exp),
            },
            "outstanding_analysis": {
                "receivables": apply_share_pct(top_n_by_field(ctx.receivables, "party_name", "amount", 10)),
                "payables": apply_share_pct(top_n_by_field(ctx.payables, "party_name", "amount", 10)),
            },
            "health_metrics": {
                "current_ratio_proxy": round(receivable_total / payable_total, 2) if payable_total else None,
                "expense_to_revenue_ratio": round(expense_total / revenue_total, 2) if revenue_total else None,
                "days_sales_outstanding_proxy": self._dso_proxy(ctx),
            },
        }

    def _dso_proxy(self, ctx: IntelligenceDataContext) -> float | None:
        receivable = sum_field(ctx.receivables, "amount")
        revenue = sum_field(ctx.sales_vouchers, "total_amount") or sum_field(ctx.sales_vouchers, "subtotal")
        if revenue <= 0:
            return None
        monthly_revenue = revenue / max(len(ctx.sales_vouchers), 1) * 30
        if monthly_revenue <= 0:
            return None
        return round(receivable / monthly_revenue * 30, 1)
