"""
Mash Voice - ASR Service (Deepgram Streaming)

Handles real-time speech-to-text using Deepgram's streaming API.
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Awaitable

from deepgram import DeepgramClient, AsyncDeepgramClient

from app.config import get_settings
from app.utils.logging import CallLogger, get_logger

logger = get_logger(__name__)


class TranscriptResult:
    """Represents a transcript result from ASR."""

    def __init__(
        self,
        text: str,
        is_final: bool,
        confidence: float,
        start_time: float,
        end_time: float,
        words: list[dict[str, Any]] | None = None,
    ):
        self.text = text
        self.is_final = is_final
        self.confidence = confidence
        self.start_time = start_time
        self.end_time = end_time
        self.words = words or []
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "is_final": self.is_final,
            "confidence": self.confidence,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "words": self.words,
            "timestamp": self.timestamp.isoformat(),
        }


class ASRSession:
    """
    Manages a single ASR session for a call.
    
    Handles streaming audio to Deepgram and receiving transcripts.
    Note: Deepgram v3 SDK uses REST/WebSocket APIs directly without event handlers.
    """

    def __init__(
        self,
        call_sid: str,
        on_transcript: Callable[[TranscriptResult], Awaitable[None]] | None = None,
        on_error: Callable[[Exception], Awaitable[None]] | None = None,
    ):
        self.call_sid = call_sid
        self.on_transcript = on_transcript
        self.on_error = on_error
        self._client: AsyncDeepgramClient | None = None
        self._is_active = False
        self._log = CallLogger(call_sid)

    async def start(self) -> None:
        """Start the ASR session."""
        settings = get_settings()
        
        try:
            # Create Deepgram async client
            self._client = AsyncDeepgramClient(
                api_key=settings.deepgram_api_key
            )
            self._is_active = True
            self._log.info("ASR session started", model="nova-2")
                
        except Exception as e:
            self._log.error("Failed to start ASR session", error=str(e))
            raise

    async def send_audio(self, audio_data: bytes) -> None:
        """Send audio data to the ASR service for transcription."""
        if not self._is_active or not self._client:
            return
            
        try:
            # Transcribe the audio using REST API (simpler than streaming)
            response = await self._client.listen.rest.v("1").transcribe_file(
                {"buffer": audio_data},
                {
                    "model": "nova-2",
                    "language": "en-US",
                    "smart_format": True,
                    "punctuate": True,
                }
            )
            
            if response and response.results:
                channels = response.results.channels
                if channels and channels[0].alternatives:
                    transcript_text = channels[0].alternatives[0].transcript
                    
                    if transcript_text:
                        transcript = TranscriptResult(
                            text=transcript_text,
                            is_final=True,
                            confidence=channels[0].alternatives[0].confidence if hasattr(channels[0].alternatives[0], 'confidence') else 0.0,
                            start_time=0.0,
                            end_time=0.0,
                        )
                        
                        self._log.info(
                            "Final transcript",
                            text=transcript_text,
                        )
                        
                        if self.on_transcript:
                            await self.on_transcript(transcript)
            
        except Exception as e:
            self._log.error("Error transcribing audio", error=str(e))
            if self.on_error:
                await self.on_error(e)

    async def stop(self) -> None:
        """Stop the ASR session."""
        self._is_active = False
        self._log.info("ASR session stopped")

    @property
    def is_active(self) -> bool:
        return self._is_active


class ASRService:
    """
    Service for managing ASR sessions across calls.
    """

    def __init__(self):
        self._sessions: dict[str, ASRSession] = {}

    async def create_session(
        self,
        call_sid: str,
        on_transcript: Callable[[TranscriptResult], Awaitable[None]] | None = None,
        on_error: Callable[[Exception], Awaitable[None]] | None = None,
    ) -> ASRSession:
        """Create a new ASR session for a call."""
        if call_sid in self._sessions:
            # Close existing session
            await self.close_session(call_sid)
        
        session = ASRSession(
            call_sid=call_sid,
            on_transcript=on_transcript,
            on_error=on_error,
        )
        await session.start()
        
        self._sessions[call_sid] = session
        return session

    def get_session(self, call_sid: str) -> ASRSession | None:
        """Get an existing ASR session."""
        return self._sessions.get(call_sid)

    async def close_session(self, call_sid: str) -> None:
        """Close an ASR session."""
        session = self._sessions.pop(call_sid, None)
        if session:
            await session.stop()

    async def close_all(self) -> None:
        """Close all ASR sessions."""
        for call_sid in list(self._sessions.keys()):
            await self.close_session(call_sid)


class DeepgramASRService:
    """
    Service for file-based (non-streaming) audio transcription.
    
    Used for transcribing WhatsApp voice messages and other audio files.
    """

    def __init__(self):
        self._settings = get_settings()
        self._client: AsyncDeepgramClient | None = None

    def _get_client(self) -> AsyncDeepgramClient:
        """Get or create Deepgram client."""
        if self._client is None:
            self._client = AsyncDeepgramClient(
                api_key=self._settings.deepgram_api_key
            )
        return self._client

    async def transcribe_audio(
        self,
        audio_data: bytes,
        mimetype: str = "audio/ogg",
        language: str = "en",
    ) -> str | None:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio bytes
            mimetype: Audio MIME type (audio/ogg, audio/mpeg, etc.)
            language: Language code
            
        Returns:
            Transcribed text or None if transcription failed
        """
        try:
            client = self._get_client()
            
            # Deepgram SDK v5 API: client.listen.v1.media.transcribe_file()
            # All options are passed as keyword arguments directly
            response = await client.listen.v1.media.transcribe_file(
                request=audio_data,
                model="nova-2",
                language=language,
                smart_format=True,
                punctuate=True,
            )
            
            # Extract transcript from response (ListenV1Response)
            if response and response.results:
                channels = response.results.channels
                if channels and len(channels) > 0 and channels[0].alternatives:
                    transcript = channels[0].alternatives[0].transcript
                    logger.info(
                        "Transcribed audio",
                        length=len(audio_data),
                        transcript_length=len(transcript) if transcript else 0,
                    )
                    return transcript.strip() if transcript else None
            
            logger.warning("No transcript returned from Deepgram")
            return None
            
        except Exception as e:
            logger.exception("Error transcribing audio", error=str(e))
            return None


# Singleton instance
_asr_service: ASRService | None = None


def get_asr_service() -> ASRService:
    """Get the ASR service singleton."""
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service
