"""
Mash Voice - ASR Service (Deepgram Streaming)

Handles real-time speech-to-text using Deepgram's streaming API.
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Awaitable

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

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
        self._client: DeepgramClient | None = None
        self._connection = None
        self._is_active = False
        self._log = CallLogger(call_sid)
        self._transcript_buffer: list[str] = []

    async def start(self) -> None:
        """Start the ASR session."""
        settings = get_settings()
        
        try:
            # Configure Deepgram client
            config = DeepgramClientOptions(
                options={"keepalive": "true"}
            )
            self._client = DeepgramClient(settings.deepgram_api_key, config)
            
            # Configure live transcription options
            options = LiveOptions(
                model="nova-2",
                language="en-US",
                smart_format=True,
                punctuate=True,
                interim_results=True,
                utterance_end_ms=1000,
                vad_events=True,
                encoding="linear16",
                sample_rate=16000,
                channels=1,
            )
            
            # Create live transcription connection
            self._connection = self._client.listen.asynclive.v("1")
            
            # Set up event handlers
            self._connection.on(LiveTranscriptionEvents.Open, self._on_open)
            self._connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
            self._connection.on(LiveTranscriptionEvents.Error, self._on_error)
            self._connection.on(LiveTranscriptionEvents.Close, self._on_close)
            self._connection.on(LiveTranscriptionEvents.UtteranceEnd, self._on_utterance_end)
            
            # Start the connection
            if await self._connection.start(options):
                self._is_active = True
                self._log.info("ASR session started", model="nova-2")
            else:
                raise RuntimeError("Failed to start Deepgram connection")
                
        except Exception as e:
            self._log.error("Failed to start ASR session", error=str(e))
            raise

    async def send_audio(self, audio_data: bytes) -> None:
        """Send audio data to the ASR service."""
        if self._connection and self._is_active:
            try:
                await self._connection.send(audio_data)
            except Exception as e:
                self._log.error("Error sending audio", error=str(e))
                if self.on_error:
                    await self.on_error(e)

    async def stop(self) -> None:
        """Stop the ASR session."""
        if self._connection:
            try:
                await self._connection.finish()
            except Exception as e:
                self._log.warning("Error closing ASR connection", error=str(e))
        
        self._is_active = False
        self._log.info("ASR session stopped")

    @property
    def is_active(self) -> bool:
        return self._is_active

    # ============ Event Handlers ============

    async def _on_open(self, *args, **kwargs) -> None:
        """Handle connection open."""
        self._log.debug("Deepgram connection opened")

    async def _on_transcript(self, *args, **kwargs) -> None:
        """Handle incoming transcript."""
        try:
            result = kwargs.get("result") or (args[1] if len(args) > 1 else None)
            if not result:
                return
            
            # Extract transcript data
            channel = result.channel
            if not channel or not channel.alternatives:
                return
            
            alternative = channel.alternatives[0]
            transcript_text = alternative.transcript
            
            if not transcript_text:
                return
            
            # Create transcript result
            transcript = TranscriptResult(
                text=transcript_text,
                is_final=result.is_final,
                confidence=alternative.confidence,
                start_time=result.start,
                end_time=result.start + result.duration,
                words=[
                    {
                        "word": w.word,
                        "start": w.start,
                        "end": w.end,
                        "confidence": w.confidence,
                    }
                    for w in (alternative.words or [])
                ],
            )
            
            if result.is_final:
                self._log.info(
                    "Final transcript",
                    text=transcript_text,
                    confidence=alternative.confidence,
                )
            else:
                self._log.debug("Partial transcript", text=transcript_text)
            
            # Invoke callback
            if self.on_transcript:
                await self.on_transcript(transcript)
                
        except Exception as e:
            self._log.exception("Error processing transcript", error=str(e))

    async def _on_error(self, *args, **kwargs) -> None:
        """Handle ASR error."""
        error = kwargs.get("error") or (args[1] if len(args) > 1 else "Unknown error")
        self._log.error("ASR error", error=str(error))
        
        if self.on_error:
            await self.on_error(Exception(str(error)))

    async def _on_close(self, *args, **kwargs) -> None:
        """Handle connection close."""
        self._is_active = False
        self._log.debug("Deepgram connection closed")

    async def _on_utterance_end(self, *args, **kwargs) -> None:
        """Handle end of utterance (VAD detected silence)."""
        self._log.debug("Utterance end detected")


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
        self._client: DeepgramClient | None = None

    def _get_client(self) -> DeepgramClient:
        """Get or create Deepgram client."""
        if self._client is None:
            self._client = DeepgramClient(self._settings.deepgram_api_key)
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
            
            # Configure transcription options
            options = {
                "model": "nova-2",
                "language": language,
                "smart_format": True,
                "punctuate": True,
            }
            
            # Prepare the source
            source = {"buffer": audio_data, "mimetype": mimetype}
            
            # Transcribe
            response = await client.listen.asyncrest.v("1").transcribe_file(
                source,
                options,
            )
            
            # Extract transcript
            if response and response.results:
                channels = response.results.channels
                if channels and channels[0].alternatives:
                    transcript = channels[0].alternatives[0].transcript
                    logger.info(
                        "Transcribed audio",
                        length=len(audio_data),
                        transcript_length=len(transcript) if transcript else 0,
                    )
                    return transcript
            
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
