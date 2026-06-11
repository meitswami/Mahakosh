"""Analytics and intelligence tables

Revision ID: 011
Revises: 010
Create Date: 2026-06-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analytics_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("report_type", sa.String(100), nullable=False),
        sa.Column("format", sa.String(20), server_default="excel", nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("parameters", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("result_path", sa.String(500), nullable=True),
        sa.Column("result_size_bytes", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analytics_reports_tenant_id", "analytics_reports", ["tenant_id"])
    op.create_index("ix_analytics_reports_report_type", "analytics_reports", ["report_type"])

    op.create_table(
        "analytics_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_type", sa.String(100), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("data", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analytics_snapshots_tenant_id", "analytics_snapshots", ["tenant_id"])
    op.create_index("ix_analytics_snapshots_snapshot_type", "analytics_snapshots", ["snapshot_type"])

    op.create_table(
        "forecast_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("forecast_type", sa.String(100), nullable=False),
        sa.Column("forecast_date", sa.Date(), nullable=False),
        sa.Column("periods_ahead", sa.Integer(), server_default="3", nullable=False),
        sa.Column("historical", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("forecast", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("methodology", sa.String(100), server_default="linear_extrapolation", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forecast_results_tenant_id", "forecast_results", ["tenant_id"])

    op.create_table(
        "anomaly_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("status", sa.String(50), server_default="open", nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anomaly_events_tenant_id", "anomaly_events", ["tenant_id"])
    op.create_index("ix_anomaly_events_event_type", "anomaly_events", ["event_type"])

    op.create_table(
        "business_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score_date", sa.Date(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("level", sa.String(50), nullable=False),
        sa.Column("components", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_business_scores_tenant_id", "business_scores", ["tenant_id"])

    op.create_table(
        "scheduled_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("report_type", sa.String(100), nullable=False),
        sa.Column("format", sa.String(20), server_default="excel", nullable=False),
        sa.Column("schedule", sa.String(20), nullable=False),
        sa.Column("parameters", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("recipients", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scheduled_reports_tenant_id", "scheduled_reports", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("scheduled_reports")
    op.drop_table("business_scores")
    op.drop_table("anomaly_events")
    op.drop_table("forecast_results")
    op.drop_table("analytics_snapshots")
    op.drop_table("analytics_reports")
