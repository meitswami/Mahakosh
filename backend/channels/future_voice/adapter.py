"""Voice-ready adapter foundation for Hindi, English, Hinglish, and regional languages."""

from typing import Any

from backend.channels.base.adapter import BaseChannelAdapter
from backend.channels.base.types import (
    ChannelCapabilities,
    ChannelType,
    IncomingMessage,
    OutgoingMessage,
)


class VoiceAdapter(BaseChannelAdapter):
    """
    Future voice channel — integrates with the same Agent Swarm and Knowledge Base.
    STT/TTS providers plug in via metadata without architecture changes.
    """

    channel_type = ChannelType.VOICE

    SUPPORTED_LANGUAGES = ("hi", "en", "hi-en", "ta", "te", "mr", "bn", "gu", "kn", "ml")

    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(chat=True, voice_upload=True, workflow_notifications=True)

    async def send(self, message: OutgoingMessage) -> dict[str, Any]:
        return {
            "status": "voice_ready",
            "text": message.text,
            "tts_pending": True,
            "languages": list(self.SUPPORTED_LANGUAGES),
            "note": "TTS integration point — text response ready for speech synthesis",
        }

    async def parse_webhook(self, payload: dict[str, Any]) -> IncomingMessage | None:
        audio_ref = payload.get("audio_url") or payload.get("audio_file_id")
        transcript = payload.get("transcript", payload.get("text", ""))
        language = payload.get("language", "en")

        if not transcript and not audio_ref:
            return None

        return IncomingMessage(
            channel=ChannelType.VOICE,
            external_user_id=str(payload.get("user_id", "")),
            external_chat_id=str(payload.get("session_id", "")),
            text=transcript or "[Voice input — STT pending]",
            metadata={
                "audio_ref": audio_ref,
                "language": language,
                "stt_provider": payload.get("stt_provider"),
            },
        )

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict[str, Any]:
        return {
            "status": "stt_ready",
            "language": language,
            "transcript": "",
            "note": "STT integration point — plug Whisper or regional ASR provider",
        }

    async def synthesize(self, text: str, language: str = "en") -> dict[str, Any]:
        return {
            "status": "tts_ready",
            "language": language,
            "text": text,
            "note": "TTS integration point — plug regional TTS provider",
        }
