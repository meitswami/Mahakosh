"""Accounting connector layer tables

Revision ID: 008
Revises: 007
Create Date: 2026-06-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounting_connectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("connector_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), server_default="disconnected", nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="1", nullable=False),
        sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounting_connectors_tenant_id", "accounting_connectors", ["tenant_id"])
    op.create_index("ix_accounting_connectors_connector_type", "accounting_connectors", ["connector_type"])

    op.create_table(
        "tally_companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("financial_year", sa.String(20), nullable=True),
        sa.Column("books_begin_from", sa.Date(), nullable=True),
        sa.Column("books_status", sa.String(50), nullable=True),
        sa.Column("voucher_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ledger_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("inventory_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["accounting_connectors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tally_companies_tenant_id", "tally_companies", ["tenant_id"])
    op.create_index("ix_tally_companies_connector_id", "tally_companies", ["connector_id"])
    op.create_index("ix_tally_companies_name", "tally_companies", ["name"])

    op.create_table(
        "ledger_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ledger_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_name", sa.String(255), nullable=False),
        sa.Column("match_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["accounting_connectors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledgers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ledger_mappings_tenant_id", "ledger_mappings", ["tenant_id"])
    op.create_index("ix_ledger_mappings_connector_id", "ledger_mappings", ["connector_id"])
    op.create_index("ix_ledger_mappings_external_name", "ledger_mappings", ["external_name"])

    op.create_table(
        "item_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_name", sa.String(255), nullable=False),
        sa.Column("match_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["accounting_connectors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_item_mappings_tenant_id", "item_mappings", ["tenant_id"])
    op.create_index("ix_item_mappings_connector_id", "item_mappings", ["connector_id"])
    op.create_index("ix_item_mappings_external_name", "item_mappings", ["external_name"])

    op.create_table(
        "voucher_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voucher_draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("export_format", sa.String(50), server_default="tally_xml", nullable=False),
        sa.Column("export_payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exported_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["tally_companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["connector_id"], ["accounting_connectors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exported_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voucher_draft_id"], ["voucher_drafts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_voucher_exports_tenant_id", "voucher_exports", ["tenant_id"])
    op.create_index("ix_voucher_exports_voucher_draft_id", "voucher_exports", ["voucher_draft_id"])

    op.create_table(
        "accounting_validations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("is_valid", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("issues", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("checks_passed", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("validated_by", sa.String(50), server_default="system", nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounting_validations_tenant_id", "accounting_validations", ["tenant_id"])
    op.create_index("ix_accounting_validations_entity_type", "accounting_validations", ["entity_type"])
    op.create_index("ix_accounting_validations_entity_id", "accounting_validations", ["entity_id"])

    op.create_table(
        "sync_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sync_type", sa.String(50), nullable=False),
        sa.Column("trigger_mode", sa.String(50), server_default="manual", nullable=False),
        sa.Column("status", sa.String(50), server_default="idle", nullable=False),
        sa.Column("schedule_cron", sa.String(100), nullable=True),
        sa.Column("folder_path", sa.String(1000), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["accounting_connectors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_jobs_tenant_id", "sync_jobs", ["tenant_id"])
    op.create_index("ix_sync_jobs_connector_id", "sync_jobs", ["connector_id"])

    op.create_table(
        "sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sync_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level", sa.String(20), server_default="info", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sync_job_id"], ["sync_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_logs_tenant_id", "sync_logs", ["tenant_id"])
    op.create_index("ix_sync_logs_sync_job_id", "sync_logs", ["sync_job_id"])


def downgrade() -> None:
    op.drop_table("sync_logs")
    op.drop_table("sync_jobs")
    op.drop_table("accounting_validations")
    op.drop_table("voucher_exports")
    op.drop_table("item_mappings")
    op.drop_table("ledger_mappings")
    op.drop_table("tally_companies")
    op.drop_table("accounting_connectors")
