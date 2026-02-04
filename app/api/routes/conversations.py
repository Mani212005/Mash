"""
Mash Voice - Conversations Routes

REST API endpoints for WhatsApp conversation management.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.state import get_state_manager
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/conversations", tags=["conversations"])


class Message(BaseModel):
    """Message model."""
    id: str
    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    message_type: str  # 'text', 'audio', 'image', 'interactive'
    agent: Optional[str] = None
    tool_calls: Optional[List[dict]] = None


class Conversation(BaseModel):
    """Conversation model."""
    id: str
    phone_number: str
    started_at: str
    last_message_at: str
    message_count: int
    status: str  # 'active', 'ended', 'escalated'
    current_agent: str
    metadata: Optional[dict] = None


@router.get("", response_model=List[Conversation])
async def list_conversations(
    status: Optional[str] = Query(None, description="Filter by status: active, ended, escalated")
):
    """
    List all WhatsApp conversations.
    
    Query Parameters:
    - status: Filter by conversation status (optional)
    
    Returns list of conversations with metadata.
    """
    try:
        state_manager = get_state_manager()
        
        # Get all conversation keys from Redis
        conv_keys = await state_manager.redis.keys("conversation:*")
        conversations = []
        
        for key in conv_keys:
            conv_data = await state_manager.redis.hgetall(key)
            if not conv_data:
                continue
            
            # Decode bytes to strings
            conv_dict = {k.decode(): v.decode() for k, v in conv_data.items()}
            
            # Filter by status if provided
            if status and conv_dict.get('status') != status:
                continue
            
            # Parse conversation data
            conversation = Conversation(
                id=conv_dict.get('id', key.decode().split(':')[1]),
                phone_number=conv_dict.get('phone_number', 'unknown'),
                started_at=conv_dict.get('started_at', datetime.utcnow().isoformat()),
                last_message_at=conv_dict.get('last_message_at', datetime.utcnow().isoformat()),
                message_count=int(conv_dict.get('message_count', 0)),
                status=conv_dict.get('status', 'active'),
                current_agent=conv_dict.get('current_agent', 'customer_service_agent'),
                metadata={}
            )
            conversations.append(conversation)
        
        # Sort by last message time (most recent first)
        conversations.sort(key=lambda x: x.last_message_at, reverse=True)
        
        return conversations
        
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """
    Get a specific conversation by ID.
    
    Path Parameters:
    - conversation_id: Unique conversation identifier
    """
    try:
        state_manager = get_state_manager()
        
        # Get conversation data from Redis
        conv_key = f"conversation:{conversation_id}"
        conv_data = await state_manager.redis.hgetall(conv_key)
        
        if not conv_data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Decode bytes to strings
        conv_dict = {k.decode(): v.decode() for k, v in conv_data.items()}
        
        return Conversation(
            id=conversation_id,
            phone_number=conv_dict.get('phone_number', 'unknown'),
            started_at=conv_dict.get('started_at', datetime.utcnow().isoformat()),
            last_message_at=conv_dict.get('last_message_at', datetime.utcnow().isoformat()),
            message_count=int(conv_dict.get('message_count', 0)),
            status=conv_dict.get('status', 'active'),
            current_agent=conv_dict.get('current_agent', 'customer_service_agent'),
            metadata={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}/messages", response_model=List[Message])
async def get_conversation_messages(conversation_id: str):
    """
    Get all messages for a specific conversation.
    
    Path Parameters:
    - conversation_id: Unique conversation identifier
    
    Returns chronological list of messages in the conversation.
    """
    try:
        state_manager = get_state_manager()
        
        # Get messages from Redis list
        messages_key = f"messages:{conversation_id}"
        message_count = await state_manager.redis.llen(messages_key)
        
        if message_count == 0:
            return []
        
        # Get all messages
        raw_messages = await state_manager.redis.lrange(messages_key, 0, -1)
        messages = []
        
        import json
        for idx, raw_msg in enumerate(raw_messages):
            try:
                msg_data = json.loads(raw_msg.decode())
                message = Message(
                    id=msg_data.get('id', f"msg_{idx}"),
                    conversation_id=conversation_id,
                    role=msg_data.get('role', 'user'),
                    content=msg_data.get('content', ''),
                    timestamp=msg_data.get('timestamp', datetime.utcnow().isoformat()),
                    message_type=msg_data.get('message_type', 'text'),
                    agent=msg_data.get('agent'),
                    tool_calls=msg_data.get('tool_calls'),
                )
                messages.append(message)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse message: {raw_msg}")
                continue
        
        return messages
        
    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
