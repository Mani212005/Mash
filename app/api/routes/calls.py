"""
Mash Voice - Call Management Routes

REST API endpoints for call management and monitoring.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func

from app.core.events import EventStore
from app.core.state import get_state_manager
from app.models import (
    Call,
    CallCreate,
    CallEventResponse,
    CallList,
    CallResponse,
    CallStatus,
    CallTimeline,
    CallTranscript,
    TranscriptSegment,
    get_db_session,
)
from app.services import get_call_manager, get_orchestrator
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("", response_model=CallList)
async def list_calls(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[CallStatus] = None,
    db=Depends(get_db_session),
):
    """
    List calls with pagination.
    """
    event_store = EventStore(db)
    
    # Get total count
    count_stmt = select(func.count(Call.id))
    if status:
        count_stmt = count_stmt.where(Call.status == status.value)
    result = await db.execute(count_stmt)
    total = result.scalar() or 0
    
    # Get calls
    offset = (page - 1) * page_size
    stmt = select(Call).order_by(Call.started_at.desc()).offset(offset).limit(page_size)
    if status:
        stmt = stmt.where(Call.status == status.value)
    result = await db.execute(stmt)
    calls = result.scalars().all()
    
    return CallList(
        calls=[CallResponse.model_validate(c) for c in calls],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/active", response_model=list[CallResponse])
async def get_active_calls(db=Depends(get_db_session)):
    """
    Get all active calls.
    """
    event_store = EventStore(db)
    calls = await event_store.get_active_calls()
    return [CallResponse.model_validate(c) for c in calls]


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(call_id: UUID, db=Depends(get_db_session)):
    """
    Get call details by ID.
    """
    event_store = EventStore(db)
    call = await event_store.get_call_by_id(call_id)
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return CallResponse.model_validate(call)


@router.post("/outbound", response_model=CallResponse)
async def create_outbound_call(
    request: Request,
    call_data: CallCreate,
    db=Depends(get_db_session),
):
    """
    Initiate an outbound call.
    """
    call_manager = get_call_manager()
    
    # Get base URL for webhooks
    base_url = str(request.base_url).rstrip("/")
    
    try:
        # Initiate call via Twilio
        call_sid = await call_manager.initiate_outbound_call(call_data, base_url)
        
        # Create call record
        event_store = EventStore(db)
        from app.config import get_settings
        settings = get_settings()
        
        call = await event_store.create_call(
            twilio_call_sid=call_sid,
            direction="outbound",
            from_number=call_data.from_number or settings.twilio_phone_number,
            to_number=call_data.to_number,
            initial_agent_id=call_data.agent_id,
            metadata=call_data.metadata,
        )
        await db.commit()
        
        return CallResponse.model_validate(call)
        
    except Exception as e:
        logger.exception("Failed to create outbound call", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")


@router.post("/{call_id}/end")
async def end_call(call_id: UUID, db=Depends(get_db_session)):
    """
    End an active call.
    """
    event_store = EventStore(db)
    call = await event_store.get_call_by_id(call_id)
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if call.status not in ("initiated", "ringing", "in-progress"):
        raise HTTPException(status_code=400, detail="Call is not active")
    
    try:
        call_manager = get_call_manager()
        call_manager.end_call(call.twilio_call_sid)
        
        # Update status
        await event_store.update_call_status(call_id, CallStatus.COMPLETED)
        await db.commit()
        
        return {"status": "ended", "call_id": str(call_id)}
        
    except Exception as e:
        logger.exception("Failed to end call", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to end call: {str(e)}")


@router.get("/{call_id}/timeline", response_model=CallTimeline)
async def get_call_timeline(call_id: UUID, db=Depends(get_db_session)):
    """
    Get event timeline for a call.
    """
    event_store = EventStore(db)
    
    call = await event_store.get_call_by_id(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    events = await event_store.get_call_timeline(call_id)
    
    # Calculate duration
    duration_ms = None
    if call.duration_seconds:
        duration_ms = call.duration_seconds * 1000
    
    return CallTimeline(
        call_id=call_id,
        events=[CallEventResponse.model_validate(e) for e in events],
        duration_ms=duration_ms,
    )


@router.get("/{call_id}/transcript", response_model=CallTranscript)
async def get_call_transcript(call_id: UUID, db=Depends(get_db_session)):
    """
    Get full transcript for a call.
    """
    event_store = EventStore(db)
    
    call = await event_store.get_call_by_id(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    transcripts = await event_store.get_call_transcripts(call_id)
    
    segments = [
        TranscriptSegment(
            speaker=t.speaker,
            text=t.text,
            is_final=t.is_final,
            timestamp=t.timestamp,
            start_time_ms=t.start_time_ms,
            end_time_ms=t.end_time_ms,
            confidence=t.confidence,
        )
        for t in transcripts
    ]
    
    return CallTranscript(call_id=call_id, segments=segments)


@router.post("/{call_id}/transfer")
async def transfer_call(
    call_id: UUID,
    target_agent: str,
    reason: Optional[str] = None,
    db=Depends(get_db_session),
):
    """
    Transfer a call to a different agent.
    """
    event_store = EventStore(db)
    
    call = await event_store.get_call_by_id(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if call.status != "in-progress":
        raise HTTPException(status_code=400, detail="Call is not active")
    
    orchestrator = get_orchestrator()
    response = await orchestrator.transfer_agent(
        call_sid=call.twilio_call_sid,
        target_agent=target_agent,
        reason=reason,
    )
    
    # Update call record
    await event_store.update_call_agent(call_id, target_agent)
    await db.commit()
    
    return {
        "status": "transferred",
        "from_agent": call.current_agent_id,
        "to_agent": target_agent,
        "greeting": response.text,
    }
