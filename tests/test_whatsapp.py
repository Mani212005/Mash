"""
Mash Voice - WhatsApp Integration Tests
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.channels.whatsapp_channel import WhatsAppChannel
from app.models.schemas import ChannelType


@pytest.mark.asyncio
async def test_verify_webhook_success(client: AsyncClient):
    """Test successful Meta webhook verify challenge."""
    with patch(
        "app.services.whatsapp_service.WhatsAppService.verify_webhook_challenge"
    ) as mock_verify:
        mock_verify.return_value = "my_challenge_token"

        response = await client.get(
            "/api/v1/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=token&hub.challenge=my_challenge_token"
        )
        assert response.status_code == 200
        assert response.text == "my_challenge_token"


@pytest.mark.asyncio
async def test_verify_webhook_failure(client: AsyncClient):
    """Test webhook verification failure."""
    with patch(
        "app.services.whatsapp_service.WhatsAppService.verify_webhook_challenge"
    ) as mock_verify:
        mock_verify.return_value = None

        response = await client.get(
            "/api/v1/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=invalid&hub.challenge=my_challenge_token"
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_whatsapp_channel_normalize_text():
    """Test normalization of text messages."""
    channel = WhatsAppChannel()
    raw_data = {
        "id": "msg_123",
        "from": "15550000000",
        "timestamp": "1675200000",
        "type": "text",
        "text": {"body": "Hello agent"},
    }
    msg = channel.normalize_message(raw_data)
    assert msg.message_id == "msg_123"
    assert msg.chat_id == "15550000000"
    assert msg.sender_id == "15550000000"
    assert msg.channel == ChannelType.WHATSAPP
    assert msg.text == "Hello agent"
    assert msg.audio_url is None


@pytest.mark.asyncio
async def test_whatsapp_channel_normalize_interactive():
    """Test normalization of interactive messages (button reply)."""
    channel = WhatsAppChannel()
    raw_data = {
        "id": "msg_123_interactive",
        "from": "15550000000",
        "timestamp": "1675200000",
        "type": "interactive",
        "interactive": {
            "type": "button_reply",
            "button_reply": {"id": "btn_opt_0", "title": "Selected Option"},
        },
    }
    msg = channel.normalize_message(raw_data)
    assert msg.message_id == "msg_123_interactive"
    assert msg.chat_id == "15550000000"
    assert msg.sender_id == "15550000000"
    assert msg.channel == ChannelType.WHATSAPP
    assert msg.text == "Selected Option"
    assert msg.audio_url is None


@pytest.mark.asyncio
async def test_whatsapp_channel_normalize_audio():
    """Test normalization of audio messages."""
    channel = WhatsAppChannel()
    raw_data = {
        "id": "msg_456",
        "from": "15550000000",
        "timestamp": "1675200000",
        "type": "audio",
        "audio": {"id": "media_id_789"},
    }
    msg = channel.normalize_message(raw_data)
    assert msg.message_id == "msg_456"
    assert msg.chat_id == "15550000000"
    assert msg.sender_id == "15550000000"
    assert msg.channel == ChannelType.WHATSAPP
    assert msg.text is None
    assert msg.audio_url == "media_id_789"


@pytest.mark.asyncio
async def test_receive_webhook_text_message():
    """Test webhook processing of a text message."""
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "msg_123",
                                    "from": "15550000000",
                                    "timestamp": "1675200000",
                                    "type": "text",
                                    "text": {"body": "Hello agent"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    channel = WhatsAppChannel()

    with (
        patch.object(
            channel._whatsapp_service, "mark_message_read", new_callable=AsyncMock
        ) as mock_read,
        patch.object(
            channel._whatsapp_service, "send_text_message", new_callable=AsyncMock
        ) as mock_send,
        patch.object(
            channel._orchestrator, "process_message", new_callable=AsyncMock
        ) as mock_process,
        patch.object(channel._state_manager, "get_state", new_callable=AsyncMock) as mock_get_state,
        patch.object(channel._state_manager, "set_state", new_callable=AsyncMock) as mock_set_state,
    ):

        mock_get_state.return_value = {
            "phone_number": "15550000000",
            "messages": [],
            "current_agent": "primary",
            "context": {},
        }

        mock_process.return_value = {
            "message": "Welcome to support",
            "agent": "support_agent",
            "next_agent": "support_agent",
            "options": ["Check order", "Talk to agent"],
        }

        mock_send_buttons = AsyncMock()
        channel._whatsapp_service.send_interactive_buttons = mock_send_buttons

        result = await channel.receive_webhook(payload)

        assert result == {"status": "ok"}
        mock_read.assert_called_once_with("msg_123")
        mock_process.assert_called_once_with(
            session_id="wa_15550000000",
            message="Hello agent",
            context={},
        )
        mock_send.assert_called_once_with(
            to_number="15550000000",
            text="Welcome to support",
        )
        mock_send_buttons.assert_called_once()
        mock_set_state.assert_called_once()


@pytest.mark.asyncio
async def test_receive_webhook_audio_message():
    """Test webhook processing of a voice/audio message."""
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "msg_456",
                                    "from": "15550000000",
                                    "timestamp": "1675200000",
                                    "type": "audio",
                                    "audio": {"id": "media_id_789"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    channel = WhatsAppChannel()

    with (
        patch.object(
            channel._whatsapp_service, "mark_message_read", new_callable=AsyncMock
        ) as mock_read,
        patch.object(
            channel._whatsapp_service, "get_media_url", new_callable=AsyncMock
        ) as mock_media_url,
        patch.object(
            channel._whatsapp_service, "download_media", new_callable=AsyncMock
        ) as mock_download,
        patch.object(
            channel._asr_service, "transcribe_audio", new_callable=AsyncMock
        ) as mock_transcribe,
        patch.object(
            channel._whatsapp_service, "send_text_message", new_callable=AsyncMock
        ) as mock_send,
        patch.object(
            channel._orchestrator, "process_message", new_callable=AsyncMock
        ) as mock_process,
        patch.object(channel._state_manager, "get_state", new_callable=AsyncMock) as mock_get_state,
        patch.object(channel._state_manager, "set_state", new_callable=AsyncMock) as mock_set_state,
    ):

        mock_media_url.return_value = "https://meta.api/media/download/789"
        mock_download.return_value = b"ogg_audio_bytes"
        mock_transcribe.return_value = "What is the weather like?"
        mock_get_state.return_value = None

        mock_process.return_value = {
            "message": "It is sunny in San Francisco",
            "agent": "weather_agent",
        }

        result = await channel.receive_webhook(payload)

        assert result == {"status": "ok"}
        mock_read.assert_called_once_with("msg_456")
        mock_media_url.assert_called_once_with("media_id_789")
        mock_download.assert_called_once_with("https://meta.api/media/download/789")
        mock_transcribe.assert_called_once_with(b"ogg_audio_bytes")
        mock_process.assert_called_once_with(
            session_id="wa_15550000000",
            message="What is the weather like?",
            context={},
        )
        mock_send.assert_called_once_with(
            to_number="15550000000",
            text="It is sunny in San Francisco",
        )
        mock_set_state.assert_called_once()
