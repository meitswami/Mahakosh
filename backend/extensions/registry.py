"""Extension registry — unified plugin loader for App Store items."""

from __future__ import annotations

from typing import Type

import structlog

from backend.extensions.base import BaseExtension, ExtensionManifest

logger = structlog.get_logger(__name__)

EXTENSION_TYPES = (
    "agent",
    "workflow",
    "connector",
    "industry_module",
    "third_party",
)


class ExtensionRegistry:
    """In-process plugin registry — scales to marketplace via extension_catalog DB table."""

    def __init__(self) -> None:
        self._extensions: dict[str, Type[BaseExtension]] = {}

    def register(self, extension_class: Type[BaseExtension]) -> Type[BaseExtension]:
        if not issubclass(extension_class, BaseExtension):
            raise TypeError(f"{extension_class} must inherit from BaseExtension")
        slug = extension_class.manifest.slug
        self._extensions[slug] = extension_class
        logger.info(
            "extension_registered",
            slug=slug,
            type=extension_class.manifest.extension_type,
            version=extension_class.manifest.version,
        )
        return extension_class

    def get(self, slug: str) -> Type[BaseExtension]:
        if slug not in self._extensions:
            raise KeyError(f"Extension '{slug}' not registered")
        return self._extensions[slug]

    def list_extensions(self, extension_type: str | None = None) -> list[ExtensionManifest]:
        manifests = [cls.manifest for cls in self._extensions.values()]
        if extension_type:
            manifests = [m for m in manifests if m.extension_type == extension_type]
        return manifests

    def registered_slugs(self) -> list[str]:
        return list(self._extensions.keys())


extension_registry = ExtensionRegistry()
