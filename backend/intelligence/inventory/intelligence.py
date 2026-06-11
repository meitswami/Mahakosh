"""Inventory intelligence — movement, dead stock, valuation, turnover."""

from __future__ import annotations

from typing import Any

from backend.intelligence.analytics.aggregators import apply_share_pct, sum_field, top_n_by_field
from backend.intelligence.analytics.data_source import IntelligenceDataContext


class InventoryIntelligence:
    def analyze(self, ctx: IntelligenceDataContext) -> dict[str, Any]:
        items = ctx.stock_items
        if not items:
            return self._empty_result()

        valued_items = []
        for item in items:
            qty = float(item.get("closing_qty") or item.get("opening_qty") or 0)
            rate = float(item.get("rate") or 0)
            valued_items.append({
                **item,
                "qty": qty,
                "valuation": round(qty * rate, 2),
            })

        total_valuation = sum_field(valued_items, "valuation")
        moving = [i for i in valued_items if float(i.get("closing_qty", 0)) != float(i.get("opening_qty", 0))]
        dead = [i for i in valued_items if float(i.get("closing_qty", 0)) <= 0 and float(i.get("opening_qty", 0)) <= 0]
        slow = [i for i in valued_items if i not in moving and i not in dead and float(i.get("closing_qty", 0)) > 0]

        top_moving = sorted(moving, key=lambda x: abs(float(x.get("closing_qty", 0)) - float(x.get("opening_qty", 0))), reverse=True)[:10]
        turnover = self._turnover_ratio(ctx, total_valuation)

        return {
            "summary": {
                "total_items": len(items),
                "total_valuation": total_valuation,
                "moving_items": len(moving),
                "dead_stock_count": len(dead),
                "slow_moving_count": len(slow),
            },
            "top_moving_items": [
                {
                    "name": i.get("name"),
                    "opening_qty": i.get("opening_qty"),
                    "closing_qty": i.get("closing_qty"),
                    "movement": round(float(i.get("closing_qty", 0)) - float(i.get("opening_qty", 0)), 2),
                    "valuation": i["valuation"],
                }
                for i in top_moving
            ],
            "dead_stock": [
                {"name": i.get("name"), "hsn_code": i.get("hsn_code"), "rate": i.get("rate")}
                for i in dead[:15]
            ],
            "slow_moving": [
                {"name": i.get("name"), "closing_qty": i.get("closing_qty"), "valuation": i["valuation"]}
                for i in slow[:15]
            ],
            "valuation_by_category": apply_share_pct(
                top_n_by_field(
                    [{"category": i.get("category") or "Uncategorized", "value": i["valuation"]} for i in valued_items],
                    "category",
                    "value",
                    10,
                )
            ),
            "inventory_turnover": turnover,
        }

    def _turnover_ratio(self, ctx: IntelligenceDataContext, inventory_value: float) -> dict[str, Any]:
        cogs = sum(
            float(v.get("subtotal") or v.get("total_amount") or 0)
            for v in ctx.purchase_vouchers
        )
        if inventory_value <= 0:
            return {"ratio": None, "days_on_hand": None, "message": "Insufficient inventory data"}
        ratio = round(cogs / inventory_value, 2)
        days = round(365 / ratio, 0) if ratio > 0 else None
        return {"ratio": ratio, "days_on_hand": days, "cogs_proxy": cogs}

    def _empty_result(self) -> dict[str, Any]:
        return {
            "summary": {"total_items": 0, "total_valuation": 0, "moving_items": 0, "dead_stock_count": 0, "slow_moving_count": 0},
            "top_moving_items": [],
            "dead_stock": [],
            "slow_moving": [],
            "valuation_by_category": [],
            "inventory_turnover": {"ratio": None, "days_on_hand": None, "message": "No stock items synced"},
        }
