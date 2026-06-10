"""Agent swarm tables

Revision ID: 004
Revises: 003
Create Date: 2026-06-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_executions", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("agent_executions", sa.Column("reasoning", sa.Text(), nullable=True))
    op.add_column("agent_executions", sa.Column("reasoning_summary", sa.Text(), nullable=True))
    op.add_column("agent_executions", sa.Column("sources", postgresql.JSONB(), server_default="[]", nullable=False))

    op.create_table(
        "agent_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("agent_version", sa.String(20), server_default="1.0.0", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("capabilities", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("status", sa.String(50), server_default="active", nullable=False),
        sa.Column("execution_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("average_runtime_ms", sa.Float(), server_default="0", nullable=False),
        sa.Column("success_rate", sa.Float(), server_default="100", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_registry_tenant_id", "agent_registry", ["tenant_id"])
    op.create_index("ix_agent_registry_agent_name", "agent_registry", ["agent_name"])
    op.create_index("ix_agent_registry_status", "agent_registry", ["status"])

    op.create_table(
        "agent_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("source_agent", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_events_tenant_id", "agent_events", ["tenant_id"])
    op.create_index("ix_agent_events_event_type", "agent_events", ["event_type"])
    op.create_index("ix_agent_events_source_agent", "agent_events", ["source_agent"])
    op.create_index("ix_agent_events_correlation_id", "agent_events", ["correlation_id"])

    op.create_table(
        "agent_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_agent", sa.String(100), nullable=False),
        sa.Column("to_agent", sa.String(100), nullable=False),
        sa.Column("message_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("reply_to", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_messages_tenant_id", "agent_messages", ["tenant_id"])
    op.create_index("ix_agent_messages_to_agent", "agent_messages", ["to_agent"])

    op.create_table(
        "agent_memory",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("memory_type", sa.String(50), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_memory_tenant_id", "agent_memory", ["tenant_id"])
    op.create_index("ix_agent_memory_memory_type", "agent_memory", ["memory_type"])
    op.create_index("ix_agent_memory_key", "agent_memory", ["key"])
    op.create_index("ix_agent_memory_session_id", "agent_memory", ["session_id"])

    op.create_table(
        "agent_health",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), server_default="idle", nullable=False),
        sa.Column("execution_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("success_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("success_rate", sa.Float(), server_default="100", nullable=False),
        sa.Column("average_runtime_ms", sa.Float(), server_default="0", nullable=False),
        sa.Column("total_runtime_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("queue_length", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_health_tenant_id", "agent_health", ["tenant_id"])
    op.create_index("ix_agent_health_agent_name", "agent_health", ["agent_name"])

    op.create_table(
        "consensus_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("consensus_value", sa.Text(), nullable=True),
        sa.Column("consensus_confidence", sa.Float(), nullable=False),
        sa.Column("agreement_ratio", sa.Float(), nullable=False),
        sa.Column("accepted", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("votes", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dissenting_agents", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["agent_executions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consensus_results_tenant_id", "consensus_results", ["tenant_id"])
    op.create_index("ix_consensus_results_field_name", "consensus_results", ["field_name"])


def downgrade() -> None:
    op.drop_table("consensus_results")
    op.drop_table("agent_health")
    op.drop_table("agent_memory")
    op.drop_table("agent_messages")
    op.drop_table("agent_events")
    op.drop_table("agent_registry")
    op.drop_column("agent_executions", "sources")
    op.drop_column("agent_executions", "reasoning_summary")
    op.drop_column("agent_executions", "reasoning")
    op.drop_column("agent_executions", "confidence")
