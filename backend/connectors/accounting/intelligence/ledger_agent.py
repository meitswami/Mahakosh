"""Ledger Intelligence Agent — analyzes and suggests ledger mappings."""

from __future__ import annotations

from typing import Any

from backend.connectors.accounting.mapping.mapping_engine import MappingEngine


class LedgerIntelligenceAgent:
    name = "ledger_intelligence"
    version = "1.0.0"

    def __init__(self):
        self._mapper = MappingEngine()

    def analyze(self, external_ledgers: list[dict[str, Any]], mahakosh_ledgers: list[dict[str, Any]], historical: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        suggestions = []
        unmapped = []
        for ext in external_ledgers:
            name = ext.get("name", "")
            match = self._mapper.match_ledger(name, mahakosh_ledgers, historical)
            if match:
                suggestions.append({
                    "external_name": name,
                    "suggested_target": match.target_name,
                    "target_id": match.target_id,
                    "match_type": match.match_type,
                    "confidence": match.confidence,
                    "reasoning": match.reasoning,
                    "source": match.source,
                })
            else:
                unmapped.append(name)

        return {
            "agent": self.name,
            "total_external": len(external_ledgers),
            "mapped": len(suggestions),
            "unmapped": len(unmapped),
            "suggestions": suggestions,
            "unmapped_names": unmapped,
            "confidence": round(sum(s["confidence"] for s in suggestions) / len(suggestions), 1) if suggestions else 0,
        }

    def search_top_parties(self, ledgers: list[dict[str, Any]], party_type: str = "customer", limit: int = 10) -> list[dict[str, Any]]:
        filtered = [
            l for l in ledgers
            if l.get("ledger_type") == party_type
            or (party_type == "customer" and "debtor" in (l.get("parent_group") or "").lower())
            or (party_type == "vendor" and "creditor" in (l.get("parent_group") or "").lower())
        ]
        sorted_ledgers = sorted(filtered, key=lambda x: abs(float(x.get("current_balance", 0))), reverse=True)
        return [
            {
                "name": l["name"],
                "balance": float(l.get("current_balance", 0)),
                "gstin": l.get("gstin"),
                "type": party_type,
            }
            for l in sorted_ledgers[:limit]
        ]

    def receivables_summary(self, ledgers: list[dict[str, Any]]) -> dict[str, Any]:
        customers = self.search_top_parties(ledgers, "customer", limit=100)
        total = sum(c["balance"] for c in customers if c["balance"] > 0)
        return {"total_receivables": total, "top_customers": customers[:10], "count": len(customers)}
