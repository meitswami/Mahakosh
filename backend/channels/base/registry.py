from typing import Type

import structlog

from backend.channels.base.adapter import BaseChannelAdapter
from backend.channels.base.types import ChannelType

logger = structlog.get_logger(__name__)


class ChannelRegistry:
    def __init__(self) -> None:
        self._adapters: dict[ChannelType, Type[BaseChannelAdapter]] = {}
        self._instances: dict[ChannelType, BaseChannelAdapter] = {}

    def register(self, adapter_class: Type[BaseChannelAdapter]) -> Type[BaseChannelAdapter]:
        self._adapters[adapter_class.channel_type] = adapter_class
        logger.info("channel_registered", channel=adapter_class.channel_type.value)
        return adapter_class

    def get(self, channel_type: ChannelType) -> BaseChannelAdapter:
        if channel_type not in self._instances:
            if channel_type not in self._adapters:
                raise KeyError(f"Channel '{channel_type.value}' not registered")
            self._instances[channel_type] = self._adapters[channel_type]()
        return self._instances[channel_type]

    def list_channels(self) -> list[dict]:
        return [
            {
                "channel_type": cls.channel_type.value,
                "capabilities": cls().capabilities().__dict__,
            }
            for cls in self._adapters.values()
        ]


channel_registry = ChannelRegistry()
