"""Base interface for AI CFO capabilities — all future CFO modules implement this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.cfo.types import CFOCapabilityType, CapabilityResult, CFORecommendation
from backend.intelligence.analytics.data_source import IntelligenceDataContext


class BaseCFOCapability(ABC):
    """
    Every AI CFO capability must:
    - Analyze tenant data and return structured results
    - Propose recommendations that require human approval before execution
    - Never auto-execute financial or compliance actions
    """

    capability_type: CFOCapabilityType

    def __init__(self, db: AsyncSession):
        self.db = db

    @abstractmethod
    async def analyze(
        self,
        tenant_id: UUID,
        ctx: IntelligenceDataContext,
        financial: dict[str, Any],
        workflow: dict[str, Any],
        health: dict[str, Any],
    ) -> CapabilityResult:
        ...

    @abstractmethod
    def recommend(
        self,
        ctx: IntelligenceDataContext,
        financial: dict[str, Any],
        analysis: CapabilityResult,
    ) -> list[CFORecommendation]:
        ...

    def requires_human_approval(self) -> bool:
        return True

    @classmethod
    def capability_info(cls) -> dict[str, str]:
        return {
            "type": cls.capability_type.value,
            "requires_approval": "true",
            "auto_execute": "false",
        }
