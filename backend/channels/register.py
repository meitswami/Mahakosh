"""Register all channel adapters."""

from backend.channels.base.registry import channel_registry
from backend.channels.email.adapter import EmailAdapter
from backend.channels.future_mobile.adapter import MobileAdapter
from backend.channels.future_voice.adapter import VoiceAdapter
from backend.channels.telegram.adapter import TelegramAdapter
from backend.channels.webchat.adapter import WebChatAdapter
from backend.channels.whatsapp.adapter import WhatsAppAdapter


def register_channels() -> None:
    channel_registry.register(TelegramAdapter)
    channel_registry.register(WhatsAppAdapter)
    channel_registry.register(EmailAdapter)
    channel_registry.register(WebChatAdapter)
    channel_registry.register(VoiceAdapter)
    channel_registry.register(MobileAdapter)


register_channels()
