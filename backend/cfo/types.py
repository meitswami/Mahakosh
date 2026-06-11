"""AI CFO domain types — foundation for future CFO capabilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class CFOCapabilityType(StrEnum):
    FINANCIAL_RECOMMENDATIONS = "financial_recommendations"
    CASH_FLOW_PLANNING = "cash_flow_planning"
    BUDGET_MONITORING = "budget_monitoring"
    COMPLIANCE_ALERTS = "compliance_alerts"
    STRATEGIC_INSIGHTS = "strategic_insights"


class RecommendationPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


class BriefingSection(StrEnum):
    WHAT_HAPPENED = "what_happened"
    WHAT_IS_HAPPENING = "what_is_happening"
    NEEDS_ATTENTION = "needs_attention"
    NEXT_ACTIONS = "next_actions"


@dataclass
class BriefingItem:
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    summary: str = ""
    section: BriefingSection = BriefingSection.WHAT_HAPPENED
    priority: RecommendationPriority = RecommendationPriority.MEDIUM
    category: str = "general"
    confidence: float = 80.0
    entity_type: str | None = None
    entity_id: str | None = None
    action_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "section": self.section.value,
            "priority": self.priority.value,
            "category": self.category,
            "confidence": self.confidence,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action_url": self.action_url,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class CFORecommendation:
    capability: CFOCapabilityType
    title: str
    description: str
    rationale: str
    priority: RecommendationPriority
    confidence: float
    requires_approval: bool = True
    suggested_action: str | None = None
    impact_estimate: dict[str, Any] = field(default_factory=dict)
    data_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability.value,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "priority": self.priority.value,
            "confidence": self.confidence,
            "requires_approval": self.requires_approval,
            "suggested_action": self.suggested_action,
            "impact_estimate": self.impact_estimate,
            "data_sources": self.data_sources,
        }


@dataclass
class CapabilityResult:
    capability: CFOCapabilityType
    status: str
    summary: str
    items: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[CFORecommendation] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability.value,
            "status": self.status,
            "summary": self.summary,
            "items": self.items,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "metrics": self.metrics,
        }
