"""Accounting digital twin tables

Revision ID: 009
Revises: 008
Create Date: 2026-06-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounting_twin_objects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sync_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("object_type", sa.String(50), nullable=False),
        sa.Column("source_system", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(500), nullable=False),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("normalized_fields", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("quality_score", sa.Numeric(5, 2), server_default="100", nullable=False),
        sa.Column("issues", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("normalization_notes", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("is_merged", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("merged_into_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["accounting_connectors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["merged_into_id"], ["accounting_twin_objects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sync_job_id"], ["sync_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounting_twin_objects_tenant_id", "accounting_twin_objects", ["tenant_id"])
    op.create_index("ix_accounting_twin_objects_object_type", "accounting_twin_objects", ["object_type"])
    op.create_index("ix_accounting_twin_objects_source_system", "accounting_twin_objects", ["source_system"])
    op.create_index("ix_accounting_twin_objects_source_id", "accounting_twin_objects", ["source_id"])
    op.create_index("ix_accounting_twin_objects_display_name", "accounting_twin_objects", ["display_name"])
    op.create_index("ix_accounting_twin_objects_quality_score", "accounting_twin_objects", ["quality_score"])
    op.create_index("ix_accounting_twin_objects_connector_id", "accounting_twin_objects", ["connector_id"])
    op.create_index("ix_accounting_twin_objects_sync_job_id", "accounting_twin_objects", ["sync_job_id"])
    op.create_index(
        "ix_accounting_twin_objects_tenant_source",
        "accounting_twin_objects",
        ["tenant_id", "source_system", "source_id", "object_type"],
        unique=True,
    )

    op.create_table(
        "accounting_normalization_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sync_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("entity_types", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("stats", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["accounting_connectors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["sync_job_id"], ["sync_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounting_normalization_jobs_tenant_id", "accounting_normalization_jobs", ["tenant_id"])
    op.create_index("ix_accounting_normalization_jobs_status", "accounting_normalization_jobs", ["status"])
    op.create_index("ix_accounting_normalization_jobs_connector_id", "accounting_normalization_jobs", ["connector_id"])

    op.create_table(
        "accounting_data_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("twin_object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_type", sa.String(100), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), server_default="warning", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), server_default="open", nullable=False),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["twin_object_id"], ["accounting_twin_objects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounting_data_issues_tenant_id", "accounting_data_issues", ["tenant_id"])
    op.create_index("ix_accounting_data_issues_twin_object_id", "accounting_data_issues", ["twin_object_id"])
    op.create_index("ix_accounting_data_issues_code", "accounting_data_issues", ["code"])
    op.create_index("ix_accounting_data_issues_severity", "accounting_data_issues", ["severity"])
    op.create_index("ix_accounting_data_issues_status", "accounting_data_issues", ["status"])

    op.create_table(
        "accounting_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("canonical_name", sa.String(500), nullable=False),
        sa.Column("alias_name", sa.String(500), nullable=False),
        sa.Column("source", sa.String(50), server_default="auto", nullable=False),
        sa.Column("twin_object_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["twin_object_id"], ["accounting_twin_objects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounting_aliases_tenant_id", "accounting_aliases", ["tenant_id"])
    op.create_index("ix_accounting_aliases_entity_type", "accounting_aliases", ["entity_type"])
    op.create_index("ix_accounting_aliases_alias_name", "accounting_aliases", ["alias_name"])
    op.create_index(
        "ix_accounting_aliases_tenant_alias",
        "accounting_aliases",
        ["tenant_id", "entity_type", "alias_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("accounting_aliases")
    op.drop_table("accounting_data_issues")
    op.drop_table("accounting_normalization_jobs")
    op.drop_table("accounting_twin_objects")
