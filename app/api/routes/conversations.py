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
        
        # Get real WhatsApp conversations (pattern: session:state:*)
        # This is where actual WhatsApp conversations are stored
        import json
        async for key in redis.scan_iter("session:state:*"):
            try:
                state_data = await redis.get(key)
                if not state_data:
                    continue
                
                state = json.loads(state_data)
                messages = state.get('messages', [])
                
                if not messages:
                    continue
                
                session_id = key.split(':')[-1]
                
                # Determine status
                conv_status = 'active'
                if state.get('ended'):
                    conv_status = 'ended'
                elif 'handoff' in state.get('current_agent', ''):
                    conv_status = 'escalated'
                
                # Filter by status if provided
                if status and conv_status != status:
                    continue
                
                # Get timestamps
                first_msg = messages[0] if messages else {}
                last_msg = messages[-1] if messages else {}
                
                conversation = Conversation(
                    id=session_id,
                    phone_number=state.get('phone_number', 'unknown'),
                    started_at=first_msg.get('timestamp', datetime.utcnow().isoformat()),
                    last_message_at=last_msg.get('timestamp', datetime.utcnow().isoformat()),
                    message_count=len(messages),
                    status=conv_status,
                    current_agent=state.get('current_agent', 'customer_service_agent'),
                    metadata=state.get('context', {})
                )
                conversations.append(conversation)
            except Exception as e:
                logger.warning(f"Error parsing session state {key}: {e}")
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
            # Try WhatsApp conversation (session:state:*)
            import json
            session_key = f"session:state:{conversation_id}"
            state_data = await redis.get(session_key)
            
            if not state_data:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            # Parse state and convert to conversation format
            state = json.loads(state_data)
            messages = state.get('messages', [])
            
            first_msg = messages[0] if messages else {}
            last_msg = messages[-1] if messages else {}
            
            conv_dict = {
                'id': conversation_id,
                'phone_number': state.get('phone_number', 'unknown'),
                'started_at': first_msg.get('timestamp', datetime.utcnow().isoformat()),
                'last_message_at': last_msg.get('timestamp', datetime.utcnow().isoformat()),
                'message_count': str(len(messages)),
                'status': 'active',
                'current_agent': state.get('current_agent', 'customer_service_agent'),
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
            # Try WhatsApp conversation (from session state)
            session_key = f"session:state:{conversation_id}"
            state_data = await redis.get(session_key)
            
            if state_data:
                state = json.loads(state_data)
                message_list = state.get('messages', [])
                
                for idx, msg_data in enumerate(message_list):
                    message = Message(
                        id=msg_data.get('message_id', f"msg_{conversation_id}_{idx}"),
                        conversation_id=conversation_id,
                        role=msg_data.get('role', 'user'),
                        content=msg_data.get('content', ''),
                        timestamp=msg_data.get('timestamp', datetime.utcnow().isoformat()),
                        message_type='text',
                        agent=msg_data.get('agent'),
                        tool_calls=None,
                    )
                    messages.append(message)
        
        return messages
        
    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
