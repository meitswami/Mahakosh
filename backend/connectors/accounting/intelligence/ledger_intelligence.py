from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.connectors.accounting.mapping.mapping_engine import MappingEngine
from backend.connectors.accounting.twin.normalizer import AccountingNormalizer
from backend.connectors.accounting.twin.repository import TwinRepository
from backend.connectors.accounting.twin.reality import IndianAccountingReality


class LedgerIntelligence:
    """Ledger matching, duplicate detection, suggestions — operates on digital twin."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapping_engine = MappingEngine()
        self.twin_repo = TwinRepository(db)
        self.normalizer = AccountingNormalizer()
        self.reality = IndianAccountingReality()

    async def _get_ledgers(self, tenant_id: UUID) -> list[dict[str, Any]]:
        twin_ledgers = await self.twin_repo.get_twin_dicts(tenant_id, "ledger")
        if twin_ledgers:
            return [
                {
                    "id": l["id"],
                    "name": l.get("name", l.get("display_name")),
                    "parent_group": l.get("parent_group"),
                    "ledger_type": l.get("ledger_type", "general"),
                    "tally_ledger_name": l.get("original_name") or l.get("name"),
                    "gstin": l.get("gstin"),
                    "quality_score": l.get("quality_score"),
                }
                for l in twin_ledgers
            ]
        from sqlalchemy import select
        from backend.models.ledger import Ledger

        result = await self.db.execute(
            select(Ledger).where(Ledger.tenant_id == tenant_id, Ledger.is_active.is_(True))
        )
        return [
            {
                "id": l.id,
                "name": l.name,
                "parent_group": l.parent_group,
                "ledger_type": l.ledger_type,
                "tally_ledger_name": l.tally_ledger_name,
                "gstin": l.gstin,
            }
            for l in result.scalars().all()
        ]

    async def _get_historical_mappings(self, tenant_id: UUID, connector_id: UUID | None) -> list[dict[str, Any]]:
        from sqlalchemy import select
        from backend.models.accounting import LedgerMapping

        query = select(LedgerMapping).where(
            LedgerMapping.tenant_id == tenant_id,
            LedgerMapping.is_confirmed.is_(True),
        )
        if connector_id:
            query = query.where(LedgerMapping.connector_id == connector_id)
        result = await self.db.execute(query)
        return [
            {
                "external_name": m.external_name,
                "ledger_id": m.ledger_id,
                "internal_name": None,
                "confidence": float(m.confidence),
            }
            for m in result.scalars().all()
        ]

    async def match_ledger(
        self,
        tenant_id: UUID,
        external_name: str,
        connector_id: UUID | None = None,
    ) -> dict[str, Any]:
        ledgers = await self._get_ledgers(tenant_id)
        historical = await self._get_historical_mappings(tenant_id, connector_id)
        for h in historical:
            if h["ledger_id"]:
                for l in ledgers:
                    if str(l["id"]) == str(h["ledger_id"]):
                        h["internal_name"] = l["name"]
                        break
        result = self.mapping_engine.match_ledger(external_name, ledgers, historical)
        return MappingEngine.to_dict(result)

    async def suggest_mappings(
        self,
        tenant_id: UUID,
        external_names: list[str],
        connector_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        return [
            await self.match_ledger(tenant_id, name, connector_id)
            for name in external_names
        ]

    async def detect_duplicates(self, tenant_id: UUID) -> list[dict[str, Any]]:
        ledgers = await self._get_ledgers(tenant_id)
        names = [l["name"] for l in ledgers]
        dupes = self.mapping_engine.detect_duplicates(names)
        return [
            {
                **d,
                "suggestion": f"Merge '{d['name_b']}' into '{d['name_a']}' — common in Indian Tally setups",
                "cleanup_action": "merge_duplicate",
            }
            for d in dupes
        ]

    async def suggest_cleanups(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """Suggest ledger cleanups based on twin quality issues."""
        suggestions: list[dict[str, Any]] = []
        dupes = await self.detect_duplicates(tenant_id)
        for d in dupes:
            suggestions.append({
                "type": "duplicate",
                "priority": "high" if d["similarity"] >= 95 else "medium",
                "message": f"Possible duplicate: '{d['name_a']}' and '{d['name_b']}' ({d['similarity']}% similar)",
                "action": "merge_duplicate",
                "details": d,
            })

        ledgers = await self._get_ledgers(tenant_id)
        for ledger in ledgers:
            if ledger.get("quality_score", 100) < 70:
                suggestions.append({
                    "type": "low_quality",
                    "priority": "medium",
                    "message": f"Ledger '{ledger['name']}' has low quality score ({ledger.get('quality_score')})",
                    "action": "review_issues",
                    "details": {"ledger_id": str(ledger["id"])},
                })
            if not ledger.get("gstin") and ledger.get("ledger_type") in ("vendor", "customer"):
                suggestions.append({
                    "type": "missing_gstin",
                    "priority": "low",
                    "message": f"Party ledger '{ledger['name']}' missing GSTIN",
                    "action": "add_gstin",
                    "details": {"ledger_id": str(ledger["id"])},
                })
        return suggestions

    async def classify_ledger(self, name: str, parent_group: str | None = None) -> dict[str, Any]:
        cleaned, notes = self.reality.clean_ledger_name(name)
        name_lower = cleaned.lower()
        parent_lower = (parent_group or "").lower()
        if "sundry debtor" in parent_lower or "debtor" in parent_lower:
            classification = "customer"
        elif "sundry creditor" in parent_lower or "creditor" in parent_lower:
            classification = "vendor"
        elif "bank" in parent_lower:
            classification = "bank"
        elif "cash" in parent_lower:
            classification = "cash"
        elif "gst" in name_lower or "tax" in name_lower:
            classification = "tax"
        elif "sales" in parent_lower:
            classification = "sales"
        elif "purchase" in parent_lower:
            classification = "purchase"
        else:
            classification = "general"
        return {
            "name": cleaned,
            "original_name": name if cleaned != name else None,
            "parent_group": parent_group,
            "classification": classification,
            "confidence": 90.0 if parent_group else 70.0,
            "normalization_notes": notes,
        }
