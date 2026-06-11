"""Communication channel tables

Revision ID: 010
Revises: 009
Create Date: 2026-06-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "communication_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), server_default="inactive", nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("webhook_url", sa.String(500), nullable=True),
        sa.Column("bot_username", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_communication_channels_tenant_id", "communication_channels", ["tenant_id"])
    op.create_index("ix_communication_channels_channel_type", "communication_channels", ["channel_type"])

    op.create_table(
        "channel_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("external_user_id", sa.String(255), nullable=False),
        sa.Column("external_chat_id", sa.String(255), nullable=False),
        sa.Column("external_username", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "channel_type", "external_user_id", name="uq_channel_users_external"),
    )
    op.create_index("ix_channel_users_tenant_id", "channel_users", ["tenant_id"])
    op.create_index("ix_channel_users_user_id", "channel_users", ["user_id"])

    op.create_table(
        "channel_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("external_chat_id", sa.String(255), nullable=False),
        sa.Column("chat_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(50), server_default="active", nullable=False),
        sa.Column("message_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chat_session_id"], ["chat_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_channel_sessions_tenant_id", "channel_sessions", ["tenant_id"])
    op.create_index("ix_channel_sessions_user_id", "channel_sessions", ["user_id"])

    op.create_table(
        "channel_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("external_message_id", sa.String(255), nullable=True),
        sa.Column("intent", sa.String(50), nullable=True),
        sa.Column("agents_used", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("transparency", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["channel_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_channel_messages_tenant_id", "channel_messages", ["tenant_id"])
    op.create_index("ix_channel_messages_session_id", "channel_messages", ["session_id"])
    op.create_index("ix_channel_messages_direction", "channel_messages", ["direction"])

    op.create_table(
        "channel_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("attachment_type", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["channel_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_channel_attachments_message_id", "channel_attachments", ["message_id"])

    op.create_table(
        "channel_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_channel_notifications_tenant_id", "channel_notifications", ["tenant_id"])
    op.create_index("ix_channel_notifications_event_type", "channel_notifications", ["event_type"])


def downgrade() -> None:
    op.drop_table("channel_notifications")
    op.drop_table("channel_attachments")
    op.drop_table("channel_messages")
    op.drop_table("channel_sessions")
    op.drop_table("channel_users")
    op.drop_table("communication_channels")
