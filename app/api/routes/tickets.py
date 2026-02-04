"""
Mash Voice - Support Tickets Routes

REST API endpoints for customer support ticket management.
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.state import get_state_manager
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/tickets", tags=["tickets"])


class SupportTicket(BaseModel):
    """Support ticket model."""
    id: str
    customer_phone: str
    issue_type: str
    description: str
    priority: str  # 'low', 'medium', 'high', 'urgent'
    status: str  # 'open', 'in_progress', 'resolved', 'closed'
    created_at: str
    updated_at: Optional[str] = None
    order_id: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


@router.get("", response_model=List[SupportTicket])
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status")
):
    """
    List all support tickets.
    
    Query Parameters:
    - status: Filter by ticket status (optional)
    
    Returns list of support tickets.
    """
    try:
        state_manager = get_state_manager()
        
        # Get all ticket keys from Redis
        ticket_keys = await state_manager.redis.keys("ticket:*")
        tickets = []
        
        import json
        for key in ticket_keys:
            ticket_data = await state_manager.redis.get(key)
            if not ticket_data:
                continue
            
            ticket_dict = json.loads(ticket_data.decode())
            
            # Filter by status if provided
            if status and ticket_dict.get('status') != status:
                continue
            
            ticket = SupportTicket(**ticket_dict)
            tickets.append(ticket)
        
        # Sort by created_at (most recent first)
        tickets.sort(key=lambda x: x.created_at, reverse=True)
        
        return tickets
        
    except Exception as e:
        logger.error(f"Error listing tickets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticket_id}", response_model=SupportTicket)
async def get_ticket(ticket_id: str):
    """
    Get a specific support ticket by ID.
    
    Path Parameters:
    - ticket_id: Unique ticket identifier
    """
    try:
        state_manager = get_state_manager()
        
        # Get ticket from Redis
        ticket_key = f"ticket:{ticket_id}"
        ticket_data = await state_manager.redis.get(ticket_key)
        
        if not ticket_data:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        import json
        ticket_dict = json.loads(ticket_data.decode())
        
        return SupportTicket(**ticket_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=SupportTicket)
async def create_ticket(ticket: SupportTicket):
    """
    Create a new support ticket.
    
    Request Body:
    - Support ticket details
    
    Returns the created ticket with generated ID and timestamps.
    """
    try:
        state_manager = get_state_manager()
        
        # Generate ticket ID if not provided
        if not ticket.id or ticket.id == "":
            ticket.id = f"TKT-{str(uuid4())[:8].upper()}"
        
        # Set timestamps
        now = datetime.utcnow().isoformat()
        ticket.created_at = now
        ticket.updated_at = now
        
        # Save to Redis
        import json
        ticket_key = f"ticket:{ticket.id}"
        await state_manager.redis.set(
            ticket_key,
            json.dumps(ticket.dict()),
            ex=86400 * 90  # Expire after 90 days
        )
        
        logger.info(f"Created ticket: {ticket.id}")
        return ticket
        
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{ticket_id}", response_model=SupportTicket)
async def update_ticket(ticket_id: str, updates: dict):
    """
    Update a support ticket.
    
    Path Parameters:
    - ticket_id: ID of the ticket to update
    
    Request Body:
    - Fields to update (status, priority, resolution_notes, etc.)
    """
    try:
        state_manager = get_state_manager()
        
        # Get existing ticket
        ticket_key = f"ticket:{ticket_id}"
        ticket_data = await state_manager.redis.get(ticket_key)
        
        if not ticket_data:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        import json
        ticket_dict = json.loads(ticket_data.decode())
        
        # Update fields
        for key, value in updates.items():
            if key in ticket_dict and key not in ['id', 'created_at']:
                ticket_dict[key] = value
        
        # Update timestamp
        ticket_dict['updated_at'] = datetime.utcnow().isoformat()
        
        # Save back to Redis
        await state_manager.redis.set(
            ticket_key,
            json.dumps(ticket_dict),
            ex=86400 * 90  # Expire after 90 days
        )
        
        logger.info(f"Updated ticket: {ticket_id}")
        return SupportTicket(**ticket_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{ticket_id}")
async def delete_ticket(ticket_id: str):
    """
    Delete a support ticket.
    
    Path Parameters:
    - ticket_id: ID of the ticket to delete
    """
    try:
        state_manager = get_state_manager()
        
        ticket_key = f"ticket:{ticket_id}"
        result = await state_manager.redis.delete(ticket_key)
        
        if result == 0:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        logger.info(f"Deleted ticket: {ticket_id}")
        return {"status": "success", "message": f"Ticket {ticket_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
