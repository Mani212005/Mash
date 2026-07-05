"""
Mash Voice - Telegram Panel Mode Loop Prevention Integration Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.channels.base_channel import BaseChannel
from app.models.schemas import Message, ChannelType
from app.services.agent_service import AgentOrchestrator


class TelegramChannel(BaseChannel):
    """Simulated Telegram Channel implementation for testing."""

    async def receive_webhook(self, request_data: dict) -> dict:
        return {"status": "ok"}

    async def send_text(self, recipient_id: str, text: str) -> dict:
        return {"recipient": recipient_id, "text": text}

    async def send_voice(self, recipient_id: str, audio_url: str) -> dict:
        return {"recipient": recipient_id, "audio_url": audio_url}

    def normalize_message(self, raw_data: dict) -> Message:
        """
        Normalize Telegram webhook payload into the channel-agnostic Message schema,
        correctly setting the `is_bot` field.
        """
        message_data = raw_data.get("message", {})
        from_data = message_data.get("from", {})

        return Message(
            message_id=str(message_data.get("message_id", "")),
            chat_id=str(message_data.get("chat", {}).get("id", "")),
            sender_id=str(from_data.get("id", "")),
            channel=ChannelType.TELEGRAM,
            text=message_data.get("text"),
            is_bot=from_data.get("is_bot", False),
        )


async def handle_telegram_webhook(
    channel: TelegramChannel, raw_payload: dict, orchestrator: AgentOrchestrator
) -> dict:
    """
    Simulated Telegram webhook handler that implements the bot loop prevention check.
    """
    # 1. Normalize message using the channel normalizer
    message = channel.normalize_message(raw_payload)

    # 2. Loop prevention check: Ignore if the message was sent by a bot
    if message.is_bot:
        return {
            "status": "ignored",
            "reason": "loop_prevention",
            "message_id": message.message_id,
        }

    # 3. Process with agent orchestrator
    response = await orchestrator.process_message(
        session_id=f"tg_{message.chat_id}", message=message.text or ""
    )

    # 4. Respond to Telegram
    await channel.send_text(message.chat_id, response.get("message", ""))

    return {"status": "processed", "response": response}


@pytest.mark.asyncio
async def test_telegram_panel_mode_real_user():
    """Verify that messages from human users are processed and replied to."""
    channel = TelegramChannel()
    orchestrator = MagicMock(spec=AgentOrchestrator)
    orchestrator.process_message = AsyncMock(
        return_value={"message": "Hello Human!", "agent": "primary_agent", "tool_calls": []}
    )

    # Payload from a human user (is_bot = False)
    payload = {
        "update_id": 10001,
        "message": {
            "message_id": 501,
            "from": {"id": 12345, "is_bot": False, "first_name": "Alice"},
            "chat": {"id": 67890},
            "text": "Hello there",
        },
    }

    result = await handle_telegram_webhook(channel, payload, orchestrator)

    assert result["status"] == "processed"
    assert orchestrator.process_message.called
    orchestrator.process_message.assert_awaited_with(
        session_id="tg_67890", message="Hello there"
    )


@pytest.mark.asyncio
async def test_telegram_panel_mode_bot_ignored():
    """Verify that messages from bots are ignored (loop prevention) in Telegram panel mode."""
    channel = TelegramChannel()
    orchestrator = MagicMock(spec=AgentOrchestrator)
    orchestrator.process_message = AsyncMock()

    # Payload from another bot (is_bot = True)
    payload = {
        "update_id": 10002,
        "message": {
            "message_id": 502,
            "from": {"id": 88888, "is_bot": True, "first_name": "SpamBot"},
            "chat": {"id": 67890},
            "text": "How can I help you?",
        },
    }

    result = await handle_telegram_webhook(channel, payload, orchestrator)

    # Must be ignored due to loop prevention
    assert result["status"] == "ignored"
    assert result["reason"] == "loop_prevention"
    assert result["message_id"] == "502"

    # Orchestrator must not be called
    assert not orchestrator.process_message.called
