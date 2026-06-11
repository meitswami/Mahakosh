from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.connectors.accounting.mapping.mapping_engine import MappingEngine
from backend.connectors.accounting.twin.repository import TwinRepository
from backend.connectors.accounting.twin.reality import IndianAccountingReality


class ItemIntelligence:
    """Item matching, HSN mapping, GST mapping, duplicate detection — operates on digital twin."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapping_engine = MappingEngine()
        self.twin_repo = TwinRepository(db)
        self.reality = IndianAccountingReality()

    async def _get_items(self, tenant_id: UUID) -> list[dict[str, Any]]:
        twin_items = await self.twin_repo.get_twin_dicts(tenant_id, "stock_item")
        if twin_items:
            return [
                {
                    "id": i["id"],
                    "name": i.get("name", i.get("display_name")),
                    "hsn_code": i.get("hsn_code"),
                    "gst_rate": i.get("gst_rate"),
                    "tally_stock_item_name": i.get("original_name") or i.get("name"),
                    "aliases": [],
                    "quality_score": i.get("quality_score"),
                }
                for i in twin_items
            ]
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from backend.models.item import Item

        result = await self.db.execute(
            select(Item)
            .options(selectinload(Item.aliases))
            .where(Item.tenant_id == tenant_id, Item.is_active.is_(True))
        )
        return [
            {
                "id": i.id,
                "name": i.name,
                "hsn_code": i.hsn_code,
                "gst_rate": float(i.gst_rate) if i.gst_rate else None,
                "tally_stock_item_name": i.tally_stock_item_name,
                "aliases": [a.alias_name for a in i.aliases],
            }
            for i in result.scalars().all()
        ]

    async def _get_historical_mappings(self, tenant_id: UUID, connector_id: UUID | None) -> list[dict[str, Any]]:
        from sqlalchemy import select
        from backend.models.accounting import ItemMapping

        query = select(ItemMapping).where(
            ItemMapping.tenant_id == tenant_id,
            ItemMapping.is_confirmed.is_(True),
        )
        if connector_id:
            query = query.where(ItemMapping.connector_id == connector_id)
        result = await self.db.execute(query)
        return [
            {
                "external_name": m.external_name,
                "item_id": m.item_id,
                "confidence": float(m.confidence),
            }
            for m in result.scalars().all()
        ]

    async def match_item(
        self,
        tenant_id: UUID,
        external_name: str,
        connector_id: UUID | None = None,
    ) -> dict[str, Any]:
        items = await self._get_items(tenant_id)
        historical = await self._get_historical_mappings(tenant_id, connector_id)
        for h in historical:
            if h["item_id"]:
                for i in items:
                    if str(i["id"]) == str(h["item_id"]):
                        h["internal_name"] = i["name"]
                        break
        result = self.mapping_engine.match_item(external_name, items, historical)
        return MappingEngine.to_dict(result)

    async def suggest_mappings(
        self,
        tenant_id: UUID,
        external_names: list[str],
        connector_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        return [await self.match_item(tenant_id, name, connector_id) for name in external_names]

    async def detect_duplicates(self, tenant_id: UUID) -> list[dict[str, Any]]:
        items = await self._get_items(tenant_id)
        dupes = self.mapping_engine.detect_duplicates([i["name"] for i in items])
        return [
            {
                **d,
                "suggestion": f"Merge stock item '{d['name_b']}' into '{d['name_a']}'",
                "cleanup_action": "merge_duplicate",
            }
            for d in dupes
        ]

    async def suggest_cleanups(self, tenant_id: UUID) -> list[dict[str, Any]]:
        suggestions: list[dict[str, Any]] = []
        dupes = await self.detect_duplicates(tenant_id)
        for d in dupes:
            suggestions.append({
                "type": "duplicate",
                "priority": "high" if d["similarity"] >= 95 else "medium",
                "message": f"Duplicate stock item: '{d['name_a']}' / '{d['name_b']}'",
                "action": "merge_duplicate",
                "details": d,
            })

        items = await self._get_items(tenant_id)
        for item in items:
            if not item.get("hsn_code"):
                suggestions.append({
                    "type": "missing_hsn",
                    "priority": "medium",
                    "message": f"Item '{item['name']}' missing HSN code",
                    "action": "add_hsn",
                    "details": {"item_id": str(item["id"])},
                })
            if item.get("gst_rate") is None:
                inferred = self.reality.infer_gst_rate_from_hsn(item.get("hsn_code"))
                if inferred is not None:
                    suggestions.append({
                        "type": "infer_gst",
                        "priority": "low",
                        "message": f"Item '{item['name']}' — infer GST rate {inferred}% from HSN",
                        "action": "apply_inferred_gst",
                        "details": {"item_id": str(item["id"]), "gst_rate": inferred},
                    })
        return suggestions

    async def map_hsn_gst(
        self,
        tenant_id: UUID,
        item_name: str,
        hsn_code: str | None = None,
    ) -> dict[str, Any]:
        items = await self._get_items(tenant_id)
        match = self.mapping_engine.match_item(item_name, items)
        gst_rate = None
        resolved_hsn = hsn_code
        if match.internal_id:
            for i in items:
                if str(i["id"]) == str(match.internal_id):
                    gst_rate = i.get("gst_rate")
                    resolved_hsn = resolved_hsn or i.get("hsn_code")
                    break
        if gst_rate is None and resolved_hsn:
            gst_rate = self.reality.infer_gst_rate_from_hsn(resolved_hsn)
            if gst_rate is None:
                hsn_prefix = resolved_hsn[:2]
                hsn_gst_map = {"01": 0, "02": 0, "03": 5, "04": 5, "10": 18, "84": 18, "85": 18}
                gst_rate = hsn_gst_map.get(hsn_prefix, 18.0)

        return {
            "item_name": item_name,
            "matched_item": match.internal_name,
            "match_confidence": match.confidence,
            "hsn_code": resolved_hsn,
            "gst_rate": gst_rate,
            "gst_rate_inferred": gst_rate is not None and hsn_code and not hsn_code == resolved_hsn,
            "classification": "goods" if resolved_hsn else "service",
        }
