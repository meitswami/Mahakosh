from typing import Any

from pydantic import BaseModel, Field


class BriefingItemResponse(BaseModel):
    id: str
    title: str
    summary: str
    section: str
    priority: str
    category: str
    confidence: float = 80.0
    entity_type: str | None = None
    entity_id: str | None = None
    action_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = None


class CEOBriefingResponse(BaseModel):
    generated_at: str
    headline: str
    health_score: dict[str, Any]
    key_metrics: dict[str, Any]
    what_happened: list[BriefingItemResponse]
    what_is_happening: list[BriefingItemResponse]
    needs_attention: list[BriefingItemResponse]
    next_actions: list[BriefingItemResponse]
    cfo_capabilities: list[dict[str, Any]] = Field(default_factory=list)
    growth: dict[str, Any] = Field(default_factory=dict)


class RecommendationReviewRequest(BaseModel):
    notes: str | None = None


class CFORecommendationResponse(BaseModel):
    id: str
    capability: str
    title: str
    description: str
    rationale: str
    priority: str
    confidence: float
    suggested_action: str | None = None
    status: str
    requires_approval: bool
    created_at: str
    expires_at: str | None = None
