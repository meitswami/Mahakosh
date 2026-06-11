"""Base plugin contract — all marketplace extensions implement this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class ExtensionManifest:
    slug: str
    name: str
    extension_type: str
    version: str = "1.0.0"
    author: str = "Mahakosh"
    description: str = ""
    entrypoint: str = ""
    permissions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)


class BaseExtension(ABC):
    """Plugin base — agents, workflows, connectors, industry modules, third-party extensions."""

    manifest: ClassVar[ExtensionManifest]

    @abstractmethod
    async def on_install(self, tenant_id: str, config: dict[str, Any]) -> None:
        """Called when a tenant installs this extension."""

    @abstractmethod
    async def on_uninstall(self, tenant_id: str) -> None:
        """Called when a tenant removes this extension."""

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Runtime health probe for marketplace monitoring."""
