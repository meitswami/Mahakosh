import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AnalyticsReport(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "analytics_reports"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(20), default="excel", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    result_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class AnalyticsSnapshot(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "analytics_snapshots"

    snapshot_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class ForecastResult(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "forecast_results"

    forecast_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    periods_ahead: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    historical: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    forecast: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    methodology: Mapped[str] = mapped_column(String(100), default="linear_extrapolation", nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class AnomalyEvent(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "anomaly_events"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class BusinessScore(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "business_scores"

    score_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    level: Mapped[str] = mapped_column(String(50), nullable=False)
    components: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class ScheduledReport(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "scheduled_reports"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(20), default="excel", nullable=False)
    schedule: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    recipients: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
