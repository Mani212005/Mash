"""
Mash Voice - WhatsApp Channel

Implements the BaseChannel interface for WhatsApp integration.
"""

from datetime import datetime
from typing import Any

from app.channels.base_channel import BaseChannel
from app.core.events import get_event_store
from app.core.state import get_state_manager
from app.models.schemas import ChannelType, Message
from app.services.agent_service import get_agent_orchestrator
from app.services.asr_service import DeepgramASRService
from app.services.whatsapp_service import WhatsAppService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class WhatsAppChannel(BaseChannel):
    """
    WhatsApp implementation of BaseChannel.
    Handles webhook parsing, normalization, agent routing, and media/ASR processing.
    """

    def __init__(self):
        self._whatsapp_service = WhatsAppService()
        self._state_manager = get_state_manager()
        self._orchestrator = get_agent_orchestrator()
        self._asr_service = DeepgramASRService()

    async def send_text(self, recipient_id: str, text: str) -> Any:
        """
        Send a text message to a recipient.
        """
        return await self._whatsapp_service.send_text_message(
            to_number=recipient_id,
            text=text,
        )

    async def send_voice(self, recipient_id: str, audio_url: str) -> Any:
        """
        Send a voice/audio message to a recipient.
        """
        return await self._whatsapp_service.send_audio_message(
            to_number=recipient_id,
            audio_url=audio_url,
        )

    def normalize_message(self, raw_data: dict[str, Any]) -> Message:
        """
        Normalize raw WhatsApp message JSON -> Message object.
        """
        message_id = raw_data.get("id", "")
        from_number = raw_data.get("from", "")

        timestamp_raw = raw_data.get("timestamp")
        if timestamp_raw:
            try:
                timestamp = datetime.fromtimestamp(int(timestamp_raw))
            except Exception:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()

        msg_type = raw_data.get("type", "text")

        text = None
        audio_url = None

        if msg_type == "text":
            text = raw_data.get("text", {}).get("body", "")
        elif msg_type == "interactive":
            interactive = raw_data.get("interactive", {})
            interactive_type = interactive.get("type")
            if interactive_type == "button_reply":
                text = interactive.get("button_reply", {}).get("title", "")
            elif interactive_type == "list_reply":
                text = interactive.get("list_reply", {}).get("title", "")
        elif msg_type == "audio":
            audio_info = raw_data.get("audio", {})
            audio_url = audio_info.get("id")

        return Message(
            message_id=message_id,
            chat_id=from_number,
            sender_id=from_number,
            channel=ChannelType.WHATSAPP,
            text=text,
            audio_url=audio_url,
            is_bot=False,
            timestamp=timestamp,
        )

    async def receive_webhook(self, request_data: dict[str, Any]) -> Any:
        """
        Process an incoming webhook payload from the channel.
        """
        event_store = await get_event_store()

        raw_messages = []
        try:
            entry = request_data.get("entry", [])
            for e in entry:
                changes = e.get("changes", [])
                for change in changes:
                    value = change.get("value", {})

                    if "messages" not in value:
                        continue

                    for msg in value.get("messages", []):
                        raw_messages.append(msg)
        except Exception as e:
            logger.exception("Error parsing webhook payload structure", error=str(e))
            return {"status": "error", "message": str(e)}

        for raw_msg in raw_messages:
            try:
                # 1. Normalize raw message JSON -> Message object
                message = self.normalize_message(raw_msg)
                session_id = f"wa_{message.sender_id}"

                logger.info(
                    "Processing normalized WhatsApp message",
                    session_id=session_id,
                    message_id=message.message_id,
                    sender_id=message.sender_id,
                )

                # 2. Emit event using Message schema dict
                await event_store.emit(
                    event_type="whatsapp.message.received",
                    data={
                        "session_id": session_id,
                        "message": message.model_dump(mode="json"),
                    },
                )

                # 3. Mark message read (sends blue checkmarks)
                try:
                    await self._whatsapp_service.mark_message_read(message.message_id)
                except Exception as e:
                    logger.warning("Failed to mark message as read", error=str(e))

                # 4. Check message type and handle media/transcription
                msg_type = raw_msg.get("type", "text")

                if msg_type == "audio":
                    media_id = message.audio_url  # Temporarily stored as media ID
                    if media_id:
                        try:
                            # Download via Meta Graph API media URL
                            download_url = await self._whatsapp_service.get_media_url(media_id)
                            message.audio_url = download_url

                            # Download media bytes
                            audio_data = await self._whatsapp_service.download_media(download_url)

                            # Pass to ASR service
                            transcript = await self._asr_service.transcribe_audio(audio_data)

                            if transcript:
                                message.transcript = transcript
                                message.text = transcript
                            else:
                                logger.warning(
                                    "ASR returned empty transcript for audio", media_id=media_id
                                )
                        except Exception as ex:
                            logger.exception(
                                "Error transcribing audio in WhatsAppChannel", error=str(ex)
                            )

                    if not message.text:
                        await self.send_text(
                            recipient_id=message.sender_id,
                            text=(
                                "Sorry, I had trouble processing your voice message. "
                                "Please try typing your message instead."
                            ),
                        )
                        continue

                elif msg_type not in ("text", "interactive"):
                    await self.send_text(
                        recipient_id=message.sender_id,
                        text="Sorry, I can only process text and voice messages at the moment.",
                    )
                    continue

                if not message.text:
                    continue

                # 5. Get or create conversation state
                state = await self._state_manager.get_state(session_id) or {
                    "phone_number": message.sender_id,
                    "messages": [],
                    "current_agent": "primary",
                    "context": {},
                }

                # Add user message to history
                state["messages"].append(
                    {
                        "role": "user",
                        "content": message.text,
                        "timestamp": message.timestamp.isoformat(),
                        "message_id": message.message_id,
                    }
                )

                # 6. Route to agent orchestrator
                response = await self._orchestrator.process_message(
                    session_id=session_id,
                    message=message.text,
                    context=state.get("context", {}),
                )

                response_text = response.get(
                    "message", "I apologize, I encountered an issue processing your request."
                )
                agent_id = response.get("agent", "primary")

                # Update state with agent response
                state["messages"].append(
                    {
                        "role": "assistant",
                        "content": response_text,
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent": agent_id,
                    }
                )

                if response.get("context_update"):
                    state["context"].update(response["context_update"])

                if response.get("next_agent"):
                    state["current_agent"] = response["next_agent"]

                # Save state
                await self._state_manager.set_state(session_id, state)

                # 7. Send text response back
                await self.send_text(
                    recipient_id=message.sender_id,
                    text=response_text,
                )

                # If there are follow-up options, send them as interactive buttons
                if response.get("options"):
                    buttons = [
                        {"id": f"opt_{i}", "title": opt[:20]}
                        for i, opt in enumerate(response["options"][:3])
                    ]
                    await self._whatsapp_service.send_interactive_buttons(
                        to_number=message.sender_id,
                        body_text="Would you like to:",
                        buttons=buttons,
                    )
            except Exception as e:
                logger.exception(
                    "Error processing individual message in WhatsAppChannel", error=str(e)
                )

        return {"status": "ok"}
