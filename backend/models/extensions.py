import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ExtensionCatalog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """App Store catalog — agents, workflows, connectors, industry modules, third-party extensions."""

    __tablename__ = "extension_catalog"
    __table_args__ = (UniqueConstraint("extension_type", "slug", name="uq_extension_catalog_slug"),)

    extension_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manifest: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TenantExtensionInstall(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Per-tenant extension installation — plugin enablement and config."""

    __tablename__ = "tenant_extension_installs"
    __table_args__ = (UniqueConstraint("tenant_id", "extension_id", name="uq_tenant_extension"),)

    extension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extension_catalog.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    installed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
