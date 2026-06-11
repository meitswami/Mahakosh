from typing import Any

from pydantic import BaseModel, Field


class InsightItem(BaseModel):
    type: str
    text: str
    confidence: float = 0.0
    severity: str | None = None
    action: str | None = None


class InsightsResponse(BaseModel):
    observations: list[InsightItem] = Field(default_factory=list)
    recommendations: list[InsightItem] = Field(default_factory=list)
    warnings: list[InsightItem] = Field(default_factory=list)
    opportunities: list[InsightItem] = Field(default_factory=list)


class NLQueryRequest(BaseModel):
    question: str
    days: int = 30


class NLQueryResponse(BaseModel):
    question: str
    answer: str
    type: str
    confidence: float
    confidence_display: str


class ReportGenerateRequest(BaseModel):
    name: str
    report_type: str
    format: str = "excel"
    parameters: dict[str, Any] = Field(default_factory=dict)


class ScheduledReportRequest(BaseModel):
    name: str
    report_type: str
    format: str = "excel"
    schedule: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    recipients: list[str] = Field(default_factory=list)


class BusinessHealthScore(BaseModel):
    score: float
    level: str
    components: dict[str, float]
    weights: dict[str, float] = Field(default_factory=dict)


class ExecutiveDashboard(BaseModel):
    revenue: float
    expenses: float
    profit: float
    profit_margin_pct: float
    gst_liability: float
    pending_approvals: int
    business_health_score: BusinessHealthScore
    top_customers: list[dict[str, Any]] = Field(default_factory=list)
    top_vendors: list[dict[str, Any]] = Field(default_factory=list)
    charts: dict[str, Any] = Field(default_factory=dict)
    insights: InsightsResponse | None = None
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
