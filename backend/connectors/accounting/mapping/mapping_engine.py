import re
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from backend.connectors.accounting.base.types import MatchResult, MatchType


class MappingEngine:
    """Smart matching: exact, fuzzy, historical, and AI-assisted ledger/item mapping."""

    FUZZY_THRESHOLD = 0.82
    HISTORICAL_BOOST = 0.1

    @classmethod
    def normalize(cls, name: str) -> str:
        cleaned = name.lower().strip()
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @classmethod
    def fuzzy_score(cls, a: str, b: str) -> float:
        return SequenceMatcher(None, cls.normalize(a), cls.normalize(b)).ratio()

    @classmethod
    def match_ledger(
        cls,
        external_name: str,
        internal_ledgers: list[dict[str, Any]],
        historical_mappings: list[dict[str, Any]] | None = None,
    ) -> MatchResult:
        historical = historical_mappings or []
        for h in historical:
            if cls.normalize(h.get("external_name", "")) == cls.normalize(external_name):
                return MatchResult(
                    external_name=external_name,
                    internal_id=h.get("ledger_id"),
                    internal_name=h.get("internal_name"),
                    match_type=MatchType.HISTORICAL,
                    confidence=min(99.0, float(h.get("confidence", 95)) + cls.HISTORICAL_BOOST * 100),
                    reasoning=f"Previously confirmed mapping to '{h.get('internal_name')}'",
                    source="historical_mapping",
                )

        for ledger in internal_ledgers:
            if cls.normalize(ledger["name"]) == cls.normalize(external_name):
                return MatchResult(
                    external_name=external_name,
                    internal_id=ledger.get("id"),
                    internal_name=ledger["name"],
                    match_type=MatchType.EXACT,
                    confidence=100.0,
                    reasoning="Exact name match",
                    source="ledger_master",
                )
            tally_name = ledger.get("tally_ledger_name")
            if tally_name and cls.normalize(tally_name) == cls.normalize(external_name):
                return MatchResult(
                    external_name=external_name,
                    internal_id=ledger.get("id"),
                    internal_name=ledger["name"],
                    match_type=MatchType.EXACT,
                    confidence=98.0,
                    reasoning=f"Exact Tally alias match ({tally_name})",
                    source="tally_alias",
                )

        best_score = 0.0
        best_ledger = None
        for ledger in internal_ledgers:
            score = cls.fuzzy_score(external_name, ledger["name"])
            if ledger.get("tally_ledger_name"):
                score = max(score, cls.fuzzy_score(external_name, ledger["tally_ledger_name"]))
            if score > best_score:
                best_score = score
                best_ledger = ledger

        if best_ledger and best_score >= cls.FUZZY_THRESHOLD:
            return MatchResult(
                external_name=external_name,
                internal_id=best_ledger.get("id"),
                internal_name=best_ledger["name"],
                match_type=MatchType.FUZZY,
                confidence=round(best_score * 100, 2),
                reasoning=f"Fuzzy match ({best_score:.0%} similarity)",
                source="fuzzy_engine",
            )

        return MatchResult(
            external_name=external_name,
            internal_id=None,
            internal_name=None,
            match_type=MatchType.UNMATCHED,
            confidence=0.0,
            reasoning="No matching ledger found",
            source="mapping_engine",
        )

    @classmethod
    def match_item(
        cls,
        external_name: str,
        internal_items: list[dict[str, Any]],
        historical_mappings: list[dict[str, Any]] | None = None,
    ) -> MatchResult:
        historical = historical_mappings or []
        for h in historical:
            if cls.normalize(h.get("external_name", "")) == cls.normalize(external_name):
                return MatchResult(
                    external_name=external_name,
                    internal_id=h.get("item_id"),
                    internal_name=h.get("internal_name"),
                    match_type=MatchType.HISTORICAL,
                    confidence=min(99.0, float(h.get("confidence", 95)) + cls.HISTORICAL_BOOST * 100),
                    reasoning=f"Previously confirmed mapping to '{h.get('internal_name')}'",
                    source="historical_mapping",
                )

        for item in internal_items:
            if cls.normalize(item["name"]) == cls.normalize(external_name):
                return MatchResult(
                    external_name=external_name,
                    internal_id=item.get("id"),
                    internal_name=item["name"],
                    match_type=MatchType.EXACT,
                    confidence=100.0,
                    reasoning="Exact item name match",
                    source="item_master",
                )
            tally_name = item.get("tally_stock_item_name")
            if tally_name and cls.normalize(tally_name) == cls.normalize(external_name):
                return MatchResult(
                    external_name=external_name,
                    internal_id=item.get("id"),
                    internal_name=item["name"],
                    match_type=MatchType.EXACT,
                    confidence=98.0,
                    reasoning=f"Exact Tally stock item alias ({tally_name})",
                    source="tally_alias",
                )
            for alias in item.get("aliases", []):
                if cls.normalize(alias) == cls.normalize(external_name):
                    return MatchResult(
                        external_name=external_name,
                        internal_id=item.get("id"),
                        internal_name=item["name"],
                        match_type=MatchType.EXACT,
                        confidence=96.0,
                        reasoning=f"Item alias match ({alias})",
                        source="item_alias",
                    )

        best_score = 0.0
        best_item = None
        for item in internal_items:
            score = cls.fuzzy_score(external_name, item["name"])
            if item.get("tally_stock_item_name"):
                score = max(score, cls.fuzzy_score(external_name, item["tally_stock_item_name"]))
            if score > best_score:
                best_score = score
                best_item = item

        if best_item and best_score >= cls.FUZZY_THRESHOLD:
            return MatchResult(
                external_name=external_name,
                internal_id=best_item.get("id"),
                internal_name=best_item["name"],
                match_type=MatchType.FUZZY,
                confidence=round(best_score * 100, 2),
                reasoning=f"Fuzzy item match ({best_score:.0%} similarity)",
                source="fuzzy_engine",
            )

        return MatchResult(
            external_name=external_name,
            internal_id=None,
            internal_name=None,
            match_type=MatchType.UNMATCHED,
            confidence=0.0,
            reasoning="No matching item found",
            source="mapping_engine",
        )

    @classmethod
    def match_gst_ledger(cls, gst_rate: float, ledger_prefix: str = "GST") -> MatchResult:
        rate_str = f"{gst_rate:g}"
        return MatchResult(
            external_name=f"GST {rate_str}%",
            internal_id=None,
            internal_name=f"{ledger_prefix} @ {rate_str}%",
            match_type=MatchType.AI_ASSISTED,
            confidence=85.0,
            reasoning=f"Standard GST ledger naming for {rate_str}% rate",
            source="gst_mapping_rules",
        )

    @classmethod
    def detect_duplicates(cls, names: list[str], threshold: float = 0.92) -> list[dict[str, Any]]:
        duplicates = []
        seen: list[tuple[str, str]] = []
        for name in names:
            norm = cls.normalize(name)
            for existing_norm, existing_name in seen:
                score = cls.fuzzy_score(norm, existing_norm)
                if score >= threshold:
                    duplicates.append({
                        "name_a": existing_name,
                        "name_b": name,
                        "similarity": round(score * 100, 2),
                    })
                    break
            else:
                seen.append((norm, name))
        return duplicates

    @classmethod
    def to_dict(cls, result: MatchResult) -> dict[str, Any]:
        return {
            "external_name": result.external_name,
            "internal_id": str(result.internal_id) if result.internal_id else None,
            "internal_name": result.internal_name,
            "match_type": result.match_type.value,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "source": result.source,
        }
