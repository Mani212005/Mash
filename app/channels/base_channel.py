"""
Mash Voice - Abstract Channel Interface
"""

from abc import ABC, abstractmethod
from typing import Any

from app.models.schemas import Message


class BaseChannel(ABC):
    """
    Abstract Base Class representing a communication channel (e.g. WhatsApp, Telegram).
    All channels must implement these methods to ensure consistent behavior across the platform.
    """

    @abstractmethod
    async def receive_webhook(self, request_data: dict[str, Any]) -> Any:
        """
        Process an incoming webhook payload from the channel.

        Args:
            request_data: Raw payload received from the webhook.

        Returns:
            Channel-specific response payload.
        """
        pass

    @abstractmethod
    async def send_text(self, recipient_id: str, text: str) -> Any:
        """
        Send a text message to a recipient.

        Args:
            recipient_id: The identifier of the user (e.g., phone number, chat ID).
            text: The text content of the message.

        Returns:
            Channel-specific status/response.
        """
        pass

    @abstractmethod
    async def send_voice(self, recipient_id: str, audio_url: str) -> Any:
        """
        Send a voice/audio message to a recipient.

        Args:
            recipient_id: The identifier of the user (e.g., phone number, chat ID).
            audio_url: The URL to the audio file (e.g., .ogg, .mp3, .wav).

        Returns:
            Channel-specific status/response.
        """
        pass

    @abstractmethod
    def normalize_message(self, raw_data: dict[str, Any]) -> Message:
        """
        Normalize raw webhook data from the channel into a channel-agnostic Message schema.

        Args:
            raw_data: Raw JSON payload/dict from the webhook.

        Returns:
            A normalized, channel-agnostic Message instance.
        """
        pass
