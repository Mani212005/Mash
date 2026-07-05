"""
Mash Voice - WhatsApp Webhook Routes

Handles incoming WhatsApp webhooks from Meta/Facebook.
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from pydantic import BaseModel

from app.channels.whatsapp_channel import WhatsAppChannel
from app.config import get_settings
from app.services.whatsapp_service import WhatsAppService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


class WebhookPayload(BaseModel):
    """WhatsApp webhook payload model."""

    object: str
    entry: list[dict[str, Any]]


@router.get("/webhook")
async def verify_webhook(
    request: Request,
):
    """
    Handle Meta webhook verification challenge.

    Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge
    to verify webhook URL ownership.
    """
    params = request.query_params
    mode = params.get("hub.mode", "")
    token = params.get("hub.verify_token", "")
    challenge = params.get("hub.challenge", "")

    whatsapp = WhatsAppService()
    result = whatsapp.verify_webhook_challenge(mode, token, challenge)

    if result:
        return Response(content=result, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Handle incoming WhatsApp webhook events.

    Processes:
    - Incoming messages (text, media, interactive responses)
    - Message status updates (sent, delivered, read)
    """
    settings = get_settings()

    # Get raw body for signature verification
    body = await request.body()

    # Verify webhook signature (optional but recommended)
    signature = request.headers.get("X-Hub-Signature-256", "")
    whatsapp = WhatsAppService()

    if settings.whatsapp_app_secret and signature:
        if not whatsapp.verify_webhook_signature(body, signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Acknowledge receipt immediately (Meta expects 200 within 20s)
    # Process messages in background
    background_tasks.add_task(process_webhook_messages, payload)

    return {"status": "ok"}


async def process_webhook_messages(payload: dict[str, Any]):
    """
    Process incoming webhook messages in background using WhatsAppChannel.

    Args:
        payload: Webhook payload from Meta
    """
    channel = WhatsAppChannel()
    await channel.receive_webhook(payload)


@router.get("/health")
async def health_check():
    """Health check endpoint for WhatsApp service."""
    return {"status": "healthy", "service": "whatsapp"}


@router.post("/send")
async def send_message(
    to_number: str,
    message: str,
):
    """
    Send a WhatsApp message (for testing/admin).

    Args:
        to_number: Recipient phone number
        message: Message text
    """
    whatsapp = WhatsAppService()
    try:
        result = await whatsapp.send_text_message(to_number, message)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await whatsapp.close()
