"""
Mash Voice - WhatsApp Service

Handles WhatsApp Business API interactions via Meta/Facebook.
"""

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any
from enum import Enum

import httpx

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class MessageType(str, Enum):
    """WhatsApp message types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    INTERACTIVE = "interactive"
    TEMPLATE = "template"
    REACTION = "reaction"


class WhatsAppMessage:
    """Represents an incoming WhatsApp message."""

    def __init__(
        self,
        message_id: str,
        from_number: str,
        timestamp: datetime,
        message_type: MessageType,
        text: str | None = None,
        media_id: str | None = None,
        media_url: str | None = None,
        caption: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        context_message_id: str | None = None,
        raw_data: dict[str, Any] | None = None,
    ):
        self.message_id = message_id
        self.from_number = from_number
        self.timestamp = timestamp
        self.message_type = message_type
        self.text = text
        self.media_id = media_id
        self.media_url = media_url
        self.caption = caption
        self.latitude = latitude
        self.longitude = longitude
        self.context_message_id = context_message_id
        self.raw_data = raw_data or {}

    @classmethod
    def from_webhook(cls, message_data: dict[str, Any], contact_data: dict[str, Any]) -> "WhatsAppMessage":
        """Create a WhatsAppMessage from webhook payload."""
        message_id = message_data.get("id", "")
        from_number = message_data.get("from", "")
        timestamp = datetime.fromtimestamp(int(message_data.get("timestamp", 0)))
        msg_type = message_data.get("type", "text")
        
        text = None
        media_id = None
        caption = None
        latitude = None
        longitude = None
        context_message_id = None
        
        # Extract context (reply-to message)
        if "context" in message_data:
            context_message_id = message_data["context"].get("id")
        
        # Parse based on message type
        if msg_type == "text":
            text = message_data.get("text", {}).get("body", "")
        elif msg_type in ("image", "audio", "video", "document", "sticker"):
            media_info = message_data.get(msg_type, {})
            media_id = media_info.get("id")
            caption = media_info.get("caption")
        elif msg_type == "location":
            location = message_data.get("location", {})
            latitude = location.get("latitude")
            longitude = location.get("longitude")
        elif msg_type == "interactive":
            # Handle button/list replies
            interactive = message_data.get("interactive", {})
            interactive_type = interactive.get("type")
            if interactive_type == "button_reply":
                text = interactive.get("button_reply", {}).get("title", "")
            elif interactive_type == "list_reply":
                text = interactive.get("list_reply", {}).get("title", "")
        
        return cls(
            message_id=message_id,
            from_number=from_number,
            timestamp=timestamp,
            message_type=MessageType(msg_type) if msg_type in MessageType.__members__.values() else MessageType.TEXT,
            text=text,
            media_id=media_id,
            caption=caption,
            latitude=latitude,
            longitude=longitude,
            context_message_id=context_message_id,
            raw_data=message_data,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "from_number": self.from_number,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type.value,
            "text": self.text,
            "media_id": self.media_id,
            "caption": self.caption,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "context_message_id": self.context_message_id,
        }


class WhatsAppService:
    """
    Service for Meta WhatsApp Business API interactions.
    
    Handles sending messages, receiving webhooks, and media management.
    """

    def __init__(self):
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    "Authorization": f"Bearer {self._settings.whatsapp_access_token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify the webhook signature from Meta.
        
        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value
            
        Returns:
            True if signature is valid
        """
        if not signature or not self._settings.whatsapp_app_secret:
            return False
        
        expected_signature = hmac.new(
            self._settings.whatsapp_app_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        # Signature format: sha256=<hash>
        provided_hash = signature.replace("sha256=", "")
        return hmac.compare_digest(expected_signature, provided_hash)

    def verify_webhook_challenge(self, mode: str, token: str, challenge: str) -> str | None:
        """
        Verify webhook subscription challenge from Meta.
        
        Args:
            mode: hub.mode parameter
            token: hub.verify_token parameter
            challenge: hub.challenge parameter
            
        Returns:
            Challenge string if valid, None otherwise
        """
        if mode == "subscribe" and token == self._settings.whatsapp_verify_token:
            logger.info("Webhook verification successful")
            return challenge
        logger.warning("Webhook verification failed", mode=mode)
        return None

    async def send_text_message(
        self,
        to_number: str,
        text: str,
        preview_url: bool = False,
        reply_to_message_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a text message via WhatsApp.
        
        Args:
            to_number: Recipient phone number (with country code, no +)
            text: Message text
            preview_url: Whether to show URL previews
            reply_to_message_id: Optional message ID to reply to
            
        Returns:
            API response data
        """
        client = await self._get_client()
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text,
            },
        }
        
        if reply_to_message_id:
            payload["context"] = {"message_id": reply_to_message_id}
        
        try:
            response = await client.post(
                self._settings.whatsapp_api_url,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(
                "Sent WhatsApp message",
                to=to_number,
                message_id=data.get("messages", [{}])[0].get("id"),
            )
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "WhatsApp API error",
                status_code=e.response.status_code,
                response=e.response.text,
            )
            raise
        except Exception as e:
            logger.exception("Failed to send WhatsApp message", error=str(e))
            raise

    async def send_interactive_buttons(
        self,
        to_number: str,
        body_text: str,
        buttons: list[dict[str, str]],
        header_text: str | None = None,
        footer_text: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an interactive message with buttons.
        
        Args:
            to_number: Recipient phone number
            body_text: Main message body
            buttons: List of buttons [{"id": "btn1", "title": "Button 1"}, ...]
            header_text: Optional header text
            footer_text: Optional footer text
            
        Returns:
            API response data
        """
        client = await self._get_client()
        
        interactive = {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": btn["id"], "title": btn["title"]}}
                    for btn in buttons[:3]  # Max 3 buttons
                ]
            },
        }
        
        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "interactive",
            "interactive": interactive,
        }
        
        response = await client.post(self._settings.whatsapp_api_url, json=payload)
        response.raise_for_status()
        return response.json()

    async def send_interactive_list(
        self,
        to_number: str,
        body_text: str,
        button_text: str,
        sections: list[dict[str, Any]],
        header_text: str | None = None,
        footer_text: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an interactive message with a list menu.
        
        Args:
            to_number: Recipient phone number
            body_text: Main message body
            button_text: Text on the list button
            sections: List sections with rows
            header_text: Optional header text
            footer_text: Optional footer text
            
        Returns:
            API response data
        """
        client = await self._get_client()
        
        interactive = {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text,
                "sections": sections,
            },
        }
        
        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "interactive",
            "interactive": interactive,
        }
        
        response = await client.post(self._settings.whatsapp_api_url, json=payload)
        response.raise_for_status()
        return response.json()

    async def send_template_message(
        self,
        to_number: str,
        template_name: str,
        language_code: str = "en",
        components: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Send a template message (for starting conversations).
        
        Args:
            to_number: Recipient phone number
            template_name: Name of the approved template
            language_code: Template language code
            components: Template components (header, body, buttons)
            
        Returns:
            API response data
        """
        client = await self._get_client()
        
        template = {
            "name": template_name,
            "language": {"code": language_code},
        }
        
        if components:
            template["components"] = components
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "template",
            "template": template,
        }
        
        response = await client.post(self._settings.whatsapp_api_url, json=payload)
        response.raise_for_status()
        return response.json()

    async def mark_message_read(self, message_id: str) -> dict[str, Any]:
        """
        Mark a message as read (sends blue checkmarks).
        
        Args:
            message_id: The message ID to mark as read
            
        Returns:
            API response data
        """
        client = await self._get_client()
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        
        response = await client.post(self._settings.whatsapp_api_url, json=payload)
        response.raise_for_status()
        return response.json()

    async def send_reaction(
        self,
        to_number: str,
        message_id: str,
        emoji: str,
    ) -> dict[str, Any]:
        """
        Send a reaction to a message.
        
        Args:
            to_number: Recipient phone number
            message_id: Message ID to react to
            emoji: Reaction emoji
            
        Returns:
            API response data
        """
        client = await self._get_client()
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "reaction",
            "reaction": {
                "message_id": message_id,
                "emoji": emoji,
            },
        }
        
        response = await client.post(self._settings.whatsapp_api_url, json=payload)
        response.raise_for_status()
        return response.json()

    async def get_media_url(self, media_id: str) -> str:
        """
        Get the download URL for a media file.
        
        Args:
            media_id: The media ID from the webhook
            
        Returns:
            Media download URL
        """
        client = await self._get_client()
        
        url = f"https://graph.facebook.com/v18.0/{media_id}"
        response = await client.get(url)
        response.raise_for_status()
        
        data = response.json()
        return data.get("url", "")

    async def download_media(self, media_url: str) -> bytes:
        """
        Download media content.
        
        Args:
            media_url: The media URL from get_media_url
            
        Returns:
            Media content as bytes
        """
        client = await self._get_client()
        response = await client.get(media_url)
        response.raise_for_status()
        return response.content

    def parse_webhook_payload(self, payload: dict[str, Any]) -> list[WhatsAppMessage]:
        """
        Parse incoming webhook payload and extract messages.
        
        Args:
            payload: Raw webhook payload
            
        Returns:
            List of WhatsAppMessage objects
        """
        messages = []
        
        try:
            entry = payload.get("entry", [])
            for e in entry:
                changes = e.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    
                    # Skip if not a message webhook
                    if "messages" not in value:
                        continue
                    
                    contacts = {c["wa_id"]: c for c in value.get("contacts", [])}
                    
                    for msg in value.get("messages", []):
                        contact = contacts.get(msg.get("from", ""), {})
                        messages.append(WhatsAppMessage.from_webhook(msg, contact))
                        
        except Exception as e:
            logger.exception("Error parsing webhook payload", error=str(e))
        
        return messages


class ConversationManager:
    """
    Manages WhatsApp conversation sessions.
    """

    def __init__(self):
        self._whatsapp = WhatsAppService()
        self._active_conversations: dict[str, dict[str, Any]] = {}

    async def close(self) -> None:
        """Close the service."""
        await self._whatsapp.close()

    async def handle_incoming_message(
        self,
        message: WhatsAppMessage,
    ) -> str:
        """
        Handle an incoming WhatsApp message.
        
        Args:
            message: The incoming WhatsApp message
            
        Returns:
            Conversation session ID
        """
        session_id = f"wa_{message.from_number}"
        
        if session_id not in self._active_conversations:
            self._active_conversations[session_id] = {
                "phone_number": message.from_number,
                "started_at": datetime.utcnow(),
                "message_count": 0,
            }
        
        self._active_conversations[session_id]["message_count"] += 1
        self._active_conversations[session_id]["last_message_at"] = datetime.utcnow()
        
        # Mark message as read
        try:
            await self._whatsapp.mark_message_read(message.message_id)
        except Exception as e:
            logger.warning("Failed to mark message as read", error=str(e))
        
        return session_id

    async def send_response(
        self,
        phone_number: str,
        text: str,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a response to a user.
        
        Args:
            phone_number: User's phone number
            text: Response text
            reply_to: Optional message ID to reply to
            
        Returns:
            API response
        """
        return await self._whatsapp.send_text_message(
            to_number=phone_number,
            text=text,
            reply_to_message_id=reply_to,
        )

    def get_active_conversations(self) -> list[str]:
        """Get list of active conversation session IDs."""
        return list(self._active_conversations.keys())

    def end_conversation(self, session_id: str) -> None:
        """End a conversation session."""
        self._active_conversations.pop(session_id, None)

    @property
    def whatsapp(self) -> WhatsAppService:
        return self._whatsapp


# Singleton instance
_conversation_manager: ConversationManager | None = None


def get_conversation_manager() -> ConversationManager:
    """Get the conversation manager singleton."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
