"""
Mash Voice - Seed Data Routes

Generate example/demo data for development and testing.
"""

from datetime import datetime, timedelta
import random
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.state import get_state_manager
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/seed", tags=["seed"])


class SeedResponse(BaseModel):
    """Response from seeding operations."""
    success: bool
    message: str
    created_count: int


@router.post("/conversations", response_model=SeedResponse)
async def seed_conversations(count: int = 10):
    """
    Generate sample conversation data for development/demo.
    
    Args:
        count: Number of example conversations to create (default: 10, max: 50)
    
    Returns:
        SeedResponse with creation status
    """
    if count < 1 or count > 50:
        raise HTTPException(status_code=400, detail="Count must be between 1 and 50")
    
    try:
        state_manager = get_state_manager()
        redis = await state_manager._get_redis()
        
        # Sample data
        sample_names = [
            "John Smith", "Sarah Johnson", "Michael Brown", "Emily Davis",
            "David Wilson", "Jessica Martinez", "James Anderson", "Jennifer Taylor",
            "Robert Thomas", "Lisa Garcia", "William Rodriguez", "Mary Hernandez",
            "Richard Moore", "Patricia Martinez", "Charles Jackson"
        ]
        
        sample_queries = [
            "What's my order status?",
            "I need to return an item",
            "Can you help me track my package?",
            "I haven't received my refund yet",
            "How do I cancel my order?",
            "What are your business hours?",
            "I have a question about my invoice",
            "Can I speak to a manager?",
            "Is there a discount available?",
            "How long does shipping take?",
        ]
        
        sample_responses = [
            "Let me look that up for you!",
            "I'd be happy to help with that.",
            "Sure, let me check your order status.",
            "I can help you process a return.",
            "Let me transfer you to our specialist.",
            "I've created a support ticket for you.",
        ]
        
        statuses = ["active", "ended", "escalated"]
        agents = [
            "customer_service_agent",
            "sales_agent", 
            "support_agent",
            "human_handoff_agent"
        ]
        
        created = 0
        now = datetime.utcnow()
        
        for i in range(count):
            # Generate random data
            name = random.choice(sample_names)
            phone_number = f"+1555{random.randint(1000000, 9999999)}"
            status = random.choice(statuses)
            current_agent = random.choice(agents)
            
            # Random timestamps (within last 7 days)
            days_ago = random.randint(0, 7)
            hours_ago = random.randint(0, 23)
            started_at = now - timedelta(days=days_ago, hours=hours_ago)
            
            # Last message more recent
            last_msg_hours = random.randint(0, hours_ago if hours_ago > 0 else 1)
            last_message_at = now - timedelta(days=days_ago, hours=last_msg_hours)
            
            # Generate conversation ID
            conv_id = f"demo_{phone_number}_{int(started_at.timestamp())}"
            
            # Create conversation metadata
            message_count = random.randint(2, 15)
            
            # Store in Redis with correct key pattern
            conv_key = f"conversation:{conv_id}"
            await redis.hset(conv_key, mapping={
                "id": conv_id,
                "phone_number": phone_number,
                "customer_name": name,
                "started_at": started_at.isoformat(),
                "last_message_at": last_message_at.isoformat(),
                "message_count": str(message_count),
                "status": status,
                "current_agent": current_agent,
            })
            
            # Set expiration (7 days for demo data)
            await redis.expire(conv_key, 604800)
            
            # Create some sample messages for this conversation
            messages_key = f"conversation:{conv_id}:messages"
            messages = []
            
            # First message (user query)
            messages.append({
                "id": f"msg_{conv_id}_1",
                "role": "user",
                "content": random.choice(sample_queries),
                "timestamp": started_at.isoformat(),
                "message_type": "text",
            })
            
            # Response
            messages.append({
                "id": f"msg_{conv_id}_2",
                "role": "assistant",
                "content": random.choice(sample_responses),
                "timestamp": (started_at + timedelta(seconds=5)).isoformat(),
                "message_type": "text",
                "agent": current_agent,
            })
            
            # Add a few more exchanges
            for j in range(min(message_count - 2, 6)):
                msg_time = started_at + timedelta(minutes=j+1)
                messages.append({
                    "id": f"msg_{conv_id}_{j+3}",
                    "role": "user" if j % 2 == 0 else "assistant",
                    "content": random.choice(sample_queries if j % 2 == 0 else sample_responses),
                    "timestamp": msg_time.isoformat(),
                    "message_type": "text",
                    "agent": current_agent if j % 2 != 0 else None,
                })
            
            # Store messages
            import json
            await redis.set(messages_key, json.dumps(messages), ex=604800)
            
            created += 1
            logger.info(f"Created demo conversation {conv_id}")
        
        return SeedResponse(
            success=True,
            message=f"Successfully created {created} demo conversations",
            created_count=created
        )
        
    except Exception as e:
        logger.error(f"Error seeding conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations")
async def clear_demo_conversations():
    """
    Clear all demo conversation data.
    
    Returns:
        SeedResponse with deletion status
    """
    try:
        state_manager = get_state_manager()
        redis = await state_manager._get_redis()
        
        # Find all demo conversations
        demo_keys = []
        async for key in redis.scan_iter("conversation:demo_*"):
            demo_keys.append(key)
        
        if demo_keys:
            await redis.delete(*demo_keys)
        
        # Also clear message keys
        msg_keys = []
        async for key in redis.scan_iter("conversation:demo_*:messages"):
            msg_keys.append(key)
        
        if msg_keys:
            await redis.delete(*msg_keys)
        
        total_deleted = len(demo_keys) + len(msg_keys)
        
        return SeedResponse(
            success=True,
            message=f"Deleted {len(demo_keys)} conversations and {len(msg_keys)} message sets",
            created_count=total_deleted
        )
        
    except Exception as e:
        logger.error(f"Error clearing demo data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
