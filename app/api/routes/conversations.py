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
        redis = await state_manager._get_redis()
        
        conversations = []
        
        # Get demo conversations (pattern: conversation:demo_*)
        async for key in redis.scan_iter("conversation:demo_*"):
            # Skip message keys
            if ":messages" in key:
                continue
                
            conv_data = await redis.hgetall(key)
            if not conv_data:
                continue
            
            # Filter by status if provided
            if status and conv_data.get('status') != status:
                continue
            
            # Parse conversation data
            conversation = Conversation(
                id=conv_data.get('id', key.split(':')[1]),
                phone_number=conv_data.get('phone_number', 'unknown'),
                started_at=conv_data.get('started_at', datetime.utcnow().isoformat()),
                last_message_at=conv_data.get('last_message_at', datetime.utcnow().isoformat()),
                message_count=int(conv_data.get('message_count', 0)),
                status=conv_data.get('status', 'active'),
                current_agent=conv_data.get('current_agent', 'customer_service_agent'),
                metadata={}
            )
            conversations.append(conversation)
        
        # Also get real WhatsApp conversations (pattern: call:context:*)
        async for key in redis.scan_iter("call:context:*"):
            try:
                context_data = await redis.get(key)
                if not context_data:
                    continue
                
                import json
                context = json.loads(context_data)
                
                # Extract conversation info
                call_sid = key.split(':')[-1]
                conv_history = context.get('conversation_history', [])
                
                if not conv_history:
                    continue
                
                # Determine status
                conv_status = 'active'
                if context.get('metadata', {}).get('ended'):
                    conv_status = 'ended'
                elif 'handoff' in context.get('current_agent_id', ''):
                    conv_status = 'escalated'
                
                # Filter by status if provided
                if status and conv_status != status:
                    continue
                
                conversation = Conversation(
                    id=call_sid,
                    phone_number=context.get('metadata', {}).get('phone_number', 'unknown'),
                    started_at=conv_history[0].get('timestamp', datetime.utcnow().isoformat()) if conv_history else datetime.utcnow().isoformat(),
                    last_message_at=conv_history[-1].get('timestamp', datetime.utcnow().isoformat()) if conv_history else datetime.utcnow().isoformat(),
                    message_count=len(conv_history),
                    status=conv_status,
                    current_agent=context.get('current_agent_id', 'customer_service_agent'),
                    metadata=context.get('metadata', {})
                )
                conversations.append(conversation)
            except Exception as e:
                logger.warning(f"Error parsing context {key}: {e}")
                continue
        
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
        redis = await state_manager._get_redis()
        
        # Try demo conversation first
        conv_key = f"conversation:{conversation_id}"
        conv_data = await redis.hgetall(conv_key)
        
        if not conv_data:
            # Try WhatsApp conversation (call:context:*)
            context_key = f"call:context:{conversation_id}"
            context_data = await redis.get(context_key)
            
            if not context_data:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            # Parse context and convert to conversation format
            import json
            context = json.loads(context_data)
            conv_history = context.get('conversation_history', [])
            
            conv_dict = {
                'id': conversation_id,
                'phone_number': context.get('metadata', {}).get('phone_number', 'unknown'),
                'started_at': conv_history[0].get('timestamp', datetime.utcnow().isoformat()) if conv_history else datetime.utcnow().isoformat(),
                'last_message_at': conv_history[-1].get('timestamp', datetime.utcnow().isoformat()) if conv_history else datetime.utcnow().isoformat(),
                'message_count': str(len(conv_history)),
                'status': 'active',
                'current_agent': context.get('current_agent_id', 'customer_service_agent'),
            }
        else:
            conv_dict = conv_data
        
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
        redis = await state_manager._get_redis()
        messages = []
        
        import json
        
        # Try demo conversation messages
        messages_key = f"conversation:{conversation_id}:messages"
        messages_data = await redis.get(messages_key)
        
        if messages_data:
            # Demo conversation format (stored as JSON)
            message_list = json.loads(messages_data)
            for msg_data in message_list:
                message = Message(
                    id=msg_data.get('id', f"msg_{conversation_id}_{len(messages)}"),
                    conversation_id=conversation_id,
                    role=msg_data.get('role', 'user'),
                    content=msg_data.get('content', ''),
                    timestamp=msg_data.get('timestamp', datetime.utcnow().isoformat()),
                    message_type=msg_data.get('message_type', 'text'),
                    agent=msg_data.get('agent'),
                    tool_calls=msg_data.get('tool_calls'),
                )
                messages.append(message)
        else:
            # Try WhatsApp conversation (from call context)
            context_key = f"call:context:{conversation_id}"
            context_data = await redis.get(context_key)
            
            if context_data:
                context = json.loads(context_data)
                conv_history = context.get('conversation_history', [])
                
                for idx, turn in enumerate(conv_history):
                    message = Message(
                        id=f"msg_{conversation_id}_{idx}",
                        conversation_id=conversation_id,
                        role=turn.get('role', 'user'),
                        content=turn.get('content', ''),
                        timestamp=turn.get('timestamp', datetime.utcnow().isoformat()),
                        message_type='text',
                        agent=turn.get('metadata', {}).get('agent'),
                        tool_calls=None,
                    )
                    messages.append(message)
        
        return messages
        
    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
