"""
Mash Voice - TTS Service (Deepgram)

Handles text-to-speech using Deepgram's TTS API.
"""

import asyncio
from typing import AsyncIterator

import httpx

from app.config import get_settings
from app.utils.logging import CallLogger, get_logger

logger = get_logger(__name__)


class TTSService:
    """
    Text-to-Speech service using Deepgram.
    
    Supports streaming TTS for low-latency audio generation.
    """

    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._settings = get_settings()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=30.0,
                    write=5.0,
                    pool=5.0,
                )
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def synthesize(
        self,
        text: str,
        voice: str = "aura-asteria-en",
        call_sid: str | None = None,
    ) -> bytes:
        """
        Synthesize text to speech and return audio bytes.
        
        Args:
            text: Text to synthesize
            voice: Deepgram voice model (default: aura-asteria-en)
            call_sid: Optional call SID for logging
            
        Returns:
            Audio bytes in linear16 format (16kHz, mono)
        """
        log = CallLogger(call_sid) if call_sid else logger
        
        client = await self._get_client()
        
        url = "https://api.deepgram.com/v1/speak"
        headers = {
            "Authorization": f"Token {self._settings.deepgram_api_key}",
            "Content-Type": "application/json",
        }
        params = {
            "model": voice,
            "encoding": "linear16",
            "sample_rate": 16000,
        }
        
        try:
            log.debug("Starting TTS synthesis", text_length=len(text), voice=voice)
            
            response = await client.post(
                url,
                headers=headers,
                params=params,
                json={"text": text},
            )
            response.raise_for_status()
            
            audio_data = response.content
            log.info(
                "TTS synthesis complete",
                text_length=len(text),
                audio_bytes=len(audio_data),
            )
            
            return audio_data
            
        except httpx.HTTPStatusError as e:
            log.error(
                "TTS API error",
                status_code=e.response.status_code,
                error=str(e),
            )
            raise
        except Exception as e:
            log.error("TTS synthesis failed", error=str(e))
            raise

    async def synthesize_streaming(
        self,
        text: str,
        voice: str = "aura-asteria-en",
        call_sid: str | None = None,
        chunk_size: int = 4096,
    ) -> AsyncIterator[bytes]:
        """
        Synthesize text to speech with streaming output.
        
        Args:
            text: Text to synthesize
            voice: Deepgram voice model
            call_sid: Optional call SID for logging
            chunk_size: Size of audio chunks to yield
            
        Yields:
            Audio chunks in linear16 format
        """
        log = CallLogger(call_sid) if call_sid else logger
        
        client = await self._get_client()
        
        url = "https://api.deepgram.com/v1/speak"
        headers = {
            "Authorization": f"Token {self._settings.deepgram_api_key}",
            "Content-Type": "application/json",
        }
        params = {
            "model": voice,
            "encoding": "linear16",
            "sample_rate": 16000,
        }
        
        try:
            log.debug("Starting streaming TTS", text_length=len(text), voice=voice)
            
            async with client.stream(
                "POST",
                url,
                headers=headers,
                params=params,
                json={"text": text},
            ) as response:
                response.raise_for_status()
                
                total_bytes = 0
                async for chunk in response.aiter_bytes(chunk_size):
                    total_bytes += len(chunk)
                    yield chunk
                
                log.info(
                    "Streaming TTS complete",
                    text_length=len(text),
                    total_bytes=total_bytes,
                )
                
        except httpx.HTTPStatusError as e:
            log.error(
                "TTS streaming API error",
                status_code=e.response.status_code,
                error=str(e),
            )
            raise
        except Exception as e:
            log.error("TTS streaming failed", error=str(e))
            raise


class TTSCache:
    """
    Simple in-memory cache for TTS audio.
    
    Useful for common phrases that are repeated often.
    """

    def __init__(self, max_size: int = 100):
        self._cache: dict[str, bytes] = {}
        self._max_size = max_size
        self._access_order: list[str] = []

    def get(self, key: str) -> bytes | None:
        """Get cached audio."""
        if key in self._cache:
            # Move to end of access order
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None

    def set(self, key: str, audio: bytes) -> None:
        """Cache audio data."""
        if key in self._cache:
            return
        
        # Evict oldest if at capacity
        while len(self._cache) >= self._max_size:
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]
        
        self._cache[key] = audio
        self._access_order.append(key)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._access_order.clear()


class CachedTTSService:
    """TTS service with caching support."""

    def __init__(self, cache_size: int = 100):
        self._tts = TTSService()
        self._cache = TTSCache(max_size=cache_size)

    async def close(self) -> None:
        await self._tts.close()

    async def synthesize(
        self,
        text: str,
        voice: str = "aura-asteria-en",
        call_sid: str | None = None,
        use_cache: bool = True,
    ) -> bytes:
        """Synthesize with caching."""
        cache_key = f"{voice}:{text}"
        
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                logger.debug("TTS cache hit", text_length=len(text))
                return cached
        
        audio = await self._tts.synthesize(text, voice, call_sid)
        
        if use_cache and len(text) < 500:  # Only cache short phrases
            self._cache.set(cache_key, audio)
        
        return audio

    async def synthesize_streaming(
        self,
        text: str,
        voice: str = "aura-asteria-en",
        call_sid: str | None = None,
        chunk_size: int = 4096,
    ) -> AsyncIterator[bytes]:
        """Streaming synthesis (no caching)."""
        async for chunk in self._tts.synthesize_streaming(
            text, voice, call_sid, chunk_size
        ):
            yield chunk


# Singleton instance
_tts_service: CachedTTSService | None = None


def get_tts_service() -> CachedTTSService:
    """Get the TTS service singleton."""
    global _tts_service
    if _tts_service is None:
        _tts_service = CachedTTSService()
    return _tts_service
