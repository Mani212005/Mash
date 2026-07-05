"""
Mash Voice - Base Channel Interface Tests
"""

import pytest
from typing import Any
from app.channels.base_channel import BaseChannel
from app.models.schemas import Message, ChannelType


class DummyChannel(BaseChannel):
    """A concrete implementation of BaseChannel for testing."""

    async def receive_webhook(self, request_data: dict[str, Any]) -> Any:
        return {"status": "received"}

    async def send_text(self, recipient_id: str, text: str) -> Any:
        return {"recipient": recipient_id, "text": text}

    async def send_voice(self, recipient_id: str, audio_url: str) -> Any:
        return {"recipient": recipient_id, "audio_url": audio_url}

    def normalize_message(self, raw_data: dict[str, Any]) -> Message:
        return Message(
            message_id=raw_data.get("message_id", "123"),
            chat_id=raw_data.get("chat_id", "456"),
            sender_id=raw_data.get("sender_id", "789"),
            channel=ChannelType.WHATSAPP,
            text=raw_data.get("text", "hello"),
            is_bot=raw_data.get("is_bot", False),
        )


def test_base_channel_abstract():
    """Verify that BaseChannel cannot be instantiated directly."""
    with pytest.raises(TypeError):
        # BaseChannel is abstract and cannot be instantiated
        BaseChannel()  # type: ignore


@pytest.mark.asyncio
async def test_dummy_channel_methods():
    """Verify that a class inheriting from BaseChannel implements and executes all required methods."""
    channel = DummyChannel()

    # Test receive_webhook
    webhook_res = await channel.receive_webhook({"data": "test"})
    assert webhook_res == {"status": "received"}

    # Test send_text
    text_res = await channel.send_text("user123", "hello world")
    assert text_res == {"recipient": "user123", "text": "hello world"}

    # Test send_voice
    voice_res = await channel.send_voice("user123", "http://example.com/audio.mp3")
    assert voice_res == {"recipient": "user123", "audio_url": "http://example.com/audio.mp3"}

    # Test normalize_message
    msg = channel.normalize_message({
        "message_id": "msg_999",
        "chat_id": "chat_888",
        "sender_id": "sender_777",
        "text": "test normalization",
        "is_bot": False,
    })
    assert isinstance(msg, Message)
    assert msg.message_id == "msg_999"
    assert msg.chat_id == "chat_888"
    assert msg.sender_id == "sender_777"
    assert msg.text == "test normalization"
    assert msg.channel == ChannelType.WHATSAPP
    assert not msg.is_bot
