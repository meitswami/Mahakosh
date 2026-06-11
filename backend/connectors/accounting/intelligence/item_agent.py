"""Item Intelligence Agent — stock item mapping and valuation insights."""

from __future__ import annotations

from typing import Any

from backend.connectors.accounting.mapping.mapping_engine import MappingEngine


class ItemIntelligenceAgent:
    name = "item_intelligence"
    version = "1.0.0"

    def __init__(self):
        self._mapper = MappingEngine()

    def analyze(self, external_items: list[dict[str, Any]], mahakosh_items: list[dict[str, Any]], historical: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        suggestions = []
        unmapped = []
        for ext in external_items:
            name = ext.get("name", "")
            match = self._mapper.match_item(name, mahakosh_items, historical)
            if match:
                suggestions.append({
                    "external_name": name,
                    "suggested_target": match.target_name,
                    "target_id": match.target_id,
                    "match_type": match.match_type,
                    "confidence": match.confidence,
                    "reasoning": match.reasoning,
                })
            else:
                unmapped.append(name)
        return {
            "agent": self.name,
            "total_external": len(external_items),
            "mapped": len(suggestions),
            "unmapped": len(unmapped),
            "suggestions": suggestions,
            "confidence": round(sum(s["confidence"] for s in suggestions) / len(suggestions), 1) if suggestions else 0,
        }

    def inventory_valuation(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        valued = []
        total = 0.0
        for item in items:
            rate = float(item.get("default_rate") or item.get("rate") or 0)
            qty = float(item.get("quantity") or item.get("closing_qty") or 0)
            value = rate * qty
            total += value
            valued.append({"name": item.get("name"), "qty": qty, "rate": rate, "value": value})
        valued.sort(key=lambda x: x["value"], reverse=True)
        return {"total_valuation": round(total, 2), "items": valued[:20], "item_count": len(items)}
