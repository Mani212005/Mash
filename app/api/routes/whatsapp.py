"""
Mash Voice - WhatsApp Webhook Routes

Handles incoming WhatsApp webhooks from Meta/Facebook.
"""

from fastapi import APIRouter, Request, Response, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Any

from app.config import get_settings
from app.services.whatsapp_service import (
    WhatsAppService,
    WhatsAppMessage,
    ConversationManager,
    get_conversation_manager,
    MessageType,
)
from app.services.agent_service import AgentOrchestrator, get_agent_orchestrator
from app.services.asr_service import DeepgramASRService
from app.core.state import StateManager, get_state_manager
from app.core.events import EventStore, get_event_store
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
    Process incoming webhook messages in background.
    
    Args:
        payload: Webhook payload from Meta
    """
    manager = get_conversation_manager()
    orchestrator = get_agent_orchestrator()
    state_manager = get_state_manager()
    event_store = get_event_store()
    
    # Parse messages from webhook
    messages = manager.whatsapp.parse_webhook_payload(payload)
    
    for message in messages:
        try:
            # Create/get session
            session_id = await manager.handle_incoming_message(message)
            
            # Log the incoming message
            logger.info(
                "Received WhatsApp message",
                session_id=session_id,
                from_number=message.from_number,
                message_type=message.message_type.value,
            )
            
            # Store event
            await event_store.emit(
                event_type="whatsapp.message.received",
                data={
                    "session_id": session_id,
                    "message": message.to_dict(),
                },
            )
            
            # Process based on message type
            if message.message_type == MessageType.TEXT:
                # Handle text message
                await process_text_message(
                    message=message,
                    session_id=session_id,
                    manager=manager,
                    orchestrator=orchestrator,
                    state_manager=state_manager,
                )
            elif message.message_type == MessageType.AUDIO:
                # Handle voice message
                await process_audio_message(
                    message=message,
                    session_id=session_id,
                    manager=manager,
                    orchestrator=orchestrator,
                    state_manager=state_manager,
                )
            elif message.message_type == MessageType.INTERACTIVE:
                # Handle button/list responses (treat as text)
                if message.text:
                    await process_text_message(
                        message=message,
                        session_id=session_id,
                        manager=manager,
                        orchestrator=orchestrator,
                        state_manager=state_manager,
                    )
            else:
                # Unsupported message type
                await manager.send_response(
                    phone_number=message.from_number,
                    text="Sorry, I can only process text and voice messages at the moment.",
                    reply_to=message.message_id,
                )
                
        except Exception as e:
            logger.exception(
                "Error processing WhatsApp message",
                message_id=message.message_id,
                error=str(e),
            )


async def process_text_message(
    message: WhatsAppMessage,
    session_id: str,
    manager: ConversationManager,
    orchestrator: AgentOrchestrator,
    state_manager: StateManager,
):
    """
    Process a text message through the agent system.
    
    Args:
        message: The WhatsApp message
        session_id: Conversation session ID
        manager: Conversation manager
        orchestrator: Agent orchestrator
        state_manager: State manager
    """
    user_text = message.text or ""
    
    # Get or create conversation state
    state = await state_manager.get_state(session_id) or {
        "phone_number": message.from_number,
        "messages": [],
        "current_agent": "primary",
        "context": {},
    }
    
    # Add user message to history
    state["messages"].append({
        "role": "user",
        "content": user_text,
        "timestamp": message.timestamp.isoformat(),
        "message_id": message.message_id,
    })
    
    # Process through agent orchestrator
    try:
        response = await orchestrator.process_message(
            session_id=session_id,
            message=user_text,
            context=state.get("context", {}),
        )
        
        # Update state with agent response
        state["messages"].append({
            "role": "assistant",
            "content": response.get("message", ""),
            "timestamp": message.timestamp.isoformat(),
            "agent": response.get("agent", "primary"),
        })
        
        if response.get("context_update"):
            state["context"].update(response["context_update"])
        
        if response.get("next_agent"):
            state["current_agent"] = response["next_agent"]
        
        # Save state
        await state_manager.set_state(session_id, state)
        
        # Send response
        response_text = response.get("message", "I apologize, I encountered an issue processing your request.")
        await manager.send_response(
            phone_number=message.from_number,
            text=response_text,
            reply_to=message.message_id,
        )
        
        # Send follow-up options if provided
        if response.get("options"):
            buttons = [
                {"id": f"opt_{i}", "title": opt[:20]}  # Max 20 chars for button
                for i, opt in enumerate(response["options"][:3])  # Max 3 buttons
            ]
            await manager.whatsapp.send_interactive_buttons(
                to_number=message.from_number,
                body_text="Would you like to:",
                buttons=buttons,
            )
            
    except Exception as e:
        logger.exception("Error in agent processing", error=str(e))
        await manager.send_response(
            phone_number=message.from_number,
            text="I apologize, but I encountered an error processing your message. Please try again.",
            reply_to=message.message_id,
        )


async def process_audio_message(
    message: WhatsAppMessage,
    session_id: str,
    manager: ConversationManager,
    orchestrator: AgentOrchestrator,
    state_manager: StateManager,
):
    """
    Process a voice message through ASR and agent system.
    
    Args:
        message: The WhatsApp message with audio
        session_id: Conversation session ID
        manager: Conversation manager
        orchestrator: Agent orchestrator
        state_manager: State manager
    """
    if not message.media_id:
        await manager.send_response(
            phone_number=message.from_number,
            text="Sorry, I couldn't process that voice message.",
            reply_to=message.message_id,
        )
        return
    
    try:
        # Get media URL
        media_url = await manager.whatsapp.get_media_url(message.media_id)
        
        # Download audio
        audio_data = await manager.whatsapp.download_media(media_url)
        
        # Transcribe using Deepgram
        asr_service = DeepgramASRService()
        transcript = await asr_service.transcribe_audio(audio_data)
        
        if transcript:
            # Create a text message with the transcript
            text_message = WhatsAppMessage(
                message_id=message.message_id,
                from_number=message.from_number,
                timestamp=message.timestamp,
                message_type=MessageType.TEXT,
                text=transcript,
                raw_data=message.raw_data,
            )
            
            # Process as text
            await process_text_message(
                message=text_message,
                session_id=session_id,
                manager=manager,
                orchestrator=orchestrator,
                state_manager=state_manager,
            )
        else:
            await manager.send_response(
                phone_number=message.from_number,
                text="Sorry, I couldn't understand the voice message. Could you please try again or type your message?",
                reply_to=message.message_id,
            )
            
    except Exception as e:
        logger.exception("Error processing audio message", error=str(e))
        await manager.send_response(
            phone_number=message.from_number,
            text="Sorry, I had trouble processing your voice message. Please try typing your message instead.",
            reply_to=message.message_id,
        )


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
