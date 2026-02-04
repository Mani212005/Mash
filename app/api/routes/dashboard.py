"""
Mash Voice - Dashboard Stats Routes

REST API endpoints for dashboard statistics.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.state import get_state_manager
from app.models import get_db_session
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/stats", tags=["dashboard"])


class DashboardStats(BaseModel):
    """Dashboard statistics model."""
    total_conversations: int
    active_conversations: int
    messages_today: int
    avg_response_time_ms: float
    escalation_rate: float
    satisfaction_score: Optional[float] = None


@router.get("", response_model=DashboardStats)
async def get_dashboard_stats():
    """
    Get dashboard statistics.
    
    Returns aggregated stats for:
    - Total conversations
    - Active conversations
    - Messages today
    - Average response time
    - Escalation rate
    """
    try:
        state_manager = get_state_manager()
        
        # Get all conversations from state
        all_conversations = await state_manager.redis.keys("conversation:*")
        total_conversations = len(all_conversations)
        
        # Count active conversations
        active_count = 0
        messages_today = 0
        total_response_time = 0
        response_count = 0
        escalated_count = 0
        
        today = datetime.utcnow().date()
        
        for conv_key in all_conversations:
            conv_data = await state_manager.redis.hgetall(conv_key)
            if not conv_data:
                continue
            
            # Check if active
            status = conv_data.get(b'status', b'').decode()
            if status == 'active':
                active_count += 1
            
            # Count escalations
            if status == 'escalated':
                escalated_count += 1
            
            # Count messages today
            last_message_at = conv_data.get(b'last_message_at')
            if last_message_at:
                last_msg_date = datetime.fromisoformat(last_message_at.decode()).date()
                if last_msg_date == today:
                    message_count = int(conv_data.get(b'message_count', 0))
                    messages_today += message_count
            
            # Calculate response times
            avg_response = conv_data.get(b'avg_response_time_ms')
            if avg_response:
                total_response_time += float(avg_response)
                response_count += 1
        
        # Calculate averages
        avg_response_time = (
            total_response_time / response_count if response_count > 0 else 0
        )
        escalation_rate = (
            escalated_count / total_conversations if total_conversations > 0 else 0
        )
        
        return DashboardStats(
            total_conversations=total_conversations,
            active_conversations=active_count,
            messages_today=messages_today,
            avg_response_time_ms=round(avg_response_time, 2),
            escalation_rate=round(escalation_rate, 4),
            satisfaction_score=0.94,  # TODO: Implement actual satisfaction tracking
        )
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        # Return zeros on error
        return DashboardStats(
            total_conversations=0,
            active_conversations=0,
            messages_today=0,
            avg_response_time_ms=0,
            escalation_rate=0,
        )
