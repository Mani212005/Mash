"""
Mash Voice - Audio Utilities
"""

import audioop
import base64
import struct
from typing import Iterator


# Twilio sends audio as mulaw 8kHz mono
TWILIO_SAMPLE_RATE = 8000
TWILIO_SAMPLE_WIDTH = 1  # 8-bit
TWILIO_CHANNELS = 1

# Deepgram expects linear16 16kHz mono
DEEPGRAM_SAMPLE_RATE = 16000
DEEPGRAM_SAMPLE_WIDTH = 2  # 16-bit
DEEPGRAM_CHANNELS = 1


def mulaw_to_linear16(mulaw_data: bytes) -> bytes:
    """
    Convert mulaw audio (Twilio format) to linear16 PCM (Deepgram format).
    
    Args:
        mulaw_data: Raw mulaw audio bytes
        
    Returns:
        Linear16 PCM audio bytes
    """
    # Convert from mulaw to linear PCM
    linear_data = audioop.ulaw2lin(mulaw_data, DEEPGRAM_SAMPLE_WIDTH)
    
    # Resample from 8kHz to 16kHz
    linear_data, _ = audioop.ratecv(
        linear_data,
        DEEPGRAM_SAMPLE_WIDTH,
        TWILIO_CHANNELS,
        TWILIO_SAMPLE_RATE,
        DEEPGRAM_SAMPLE_RATE,
        None,
    )
    
    return linear_data


def linear16_to_mulaw(linear_data: bytes) -> bytes:
    """
    Convert linear16 PCM (Deepgram TTS) to mulaw (Twilio format).
    
    Args:
        linear_data: Linear16 PCM audio bytes at 16kHz or other sample rate
        
    Returns:
        Mulaw audio bytes at 8kHz
    """
    # Resample from input rate to 8kHz
    linear_data, _ = audioop.ratecv(
        linear_data,
        DEEPGRAM_SAMPLE_WIDTH,
        DEEPGRAM_CHANNELS,
        DEEPGRAM_SAMPLE_RATE,
        TWILIO_SAMPLE_RATE,
        None,
    )
    
    # Convert to mulaw
    mulaw_data = audioop.lin2ulaw(linear_data, DEEPGRAM_SAMPLE_WIDTH)
    
    return mulaw_data


def decode_twilio_audio(payload: str) -> bytes:
    """
    Decode base64 audio payload from Twilio media stream.
    
    Args:
        payload: Base64-encoded audio payload
        
    Returns:
        Raw audio bytes
    """
    return base64.b64decode(payload)


def encode_twilio_audio(audio_data: bytes) -> str:
    """
    Encode audio data for Twilio media stream.
    
    Args:
        audio_data: Raw audio bytes (should be mulaw 8kHz)
        
    Returns:
        Base64-encoded string
    """
    return base64.b64encode(audio_data).decode("utf-8")


def chunk_audio(audio_data: bytes, chunk_size: int = 640) -> Iterator[bytes]:
    """
    Split audio data into chunks suitable for streaming.
    
    Args:
        audio_data: Raw audio bytes
        chunk_size: Size of each chunk in bytes (default 640 = 20ms at 16kHz 16-bit)
        
    Yields:
        Audio chunks
    """
    for i in range(0, len(audio_data), chunk_size):
        yield audio_data[i : i + chunk_size]


def calculate_audio_duration_ms(audio_bytes: bytes, sample_rate: int, sample_width: int) -> float:
    """
    Calculate the duration of audio in milliseconds.
    
    Args:
        audio_bytes: Raw audio data
        sample_rate: Sample rate in Hz
        sample_width: Bytes per sample
        
    Returns:
        Duration in milliseconds
    """
    num_samples = len(audio_bytes) // sample_width
    duration_seconds = num_samples / sample_rate
    return duration_seconds * 1000


def generate_silence(duration_ms: float, sample_rate: int = DEEPGRAM_SAMPLE_RATE) -> bytes:
    """
    Generate silence audio data.
    
    Args:
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz
        
    Returns:
        Linear16 PCM silence bytes
    """
    num_samples = int(sample_rate * duration_ms / 1000)
    return b"\x00\x00" * num_samples  # 16-bit silence


def get_audio_level(audio_data: bytes, sample_width: int = 2) -> float:
    """
    Calculate the RMS level of audio data.
    
    Args:
        audio_data: Raw audio bytes
        sample_width: Bytes per sample
        
    Returns:
        RMS level (0.0 to 1.0)
    """
    if not audio_data:
        return 0.0
    
    rms = audioop.rms(audio_data, sample_width)
    # Normalize to 0-1 range (max for 16-bit is 32768)
    max_value = 2 ** (sample_width * 8 - 1)
    return min(rms / max_value, 1.0)
