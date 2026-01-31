"""
Mash Voice - Event Store

Records and retrieves call events for debugging and observability.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Call, CallEvent, Transcript, ToolInvocation
from app.models.schemas import EventType, CallStatus
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EventStore:
    """Stores and retrieves call events."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============ Call Events ============

    async def record_event(
        self,
        call_id: uuid.UUID,
        event_type: EventType,
        data: dict[str, Any] | None = None,
        latency_ms: float | None = None,
    ) -> CallEvent:
        """Record a call event."""
        event = CallEvent(
            call_id=call_id,
            event_type=event_type.value,
            timestamp=datetime.utcnow(),
            data=data or {},
            latency_ms=latency_ms,
        )
        self.session.add(event)
        await self.session.flush()
        
        logger.debug(
            "Recorded event",
            call_id=str(call_id),
            event_type=event_type.value,
            latency_ms=latency_ms,
        )
        return event

    async def get_call_timeline(self, call_id: uuid.UUID) -> list[CallEvent]:
        """Get all events for a call in chronological order."""
        stmt = (
            select(CallEvent)
            .where(CallEvent.call_id == call_id)
            .order_by(CallEvent.timestamp)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_events_by_type(
        self, call_id: uuid.UUID, event_type: EventType
    ) -> list[CallEvent]:
        """Get events of a specific type for a call."""
        stmt = (
            select(CallEvent)
            .where(CallEvent.call_id == call_id, CallEvent.event_type == event_type.value)
            .order_by(CallEvent.timestamp)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ============ Call Management ============

    async def create_call(
        self,
        twilio_call_sid: str,
        direction: str,
        from_number: str,
        to_number: str,
        initial_agent_id: str = "primary_agent",
        metadata: dict[str, Any] | None = None,
    ) -> Call:
        """Create a new call record."""
        call = Call(
            twilio_call_sid=twilio_call_sid,
            direction=direction,
            from_number=from_number,
            to_number=to_number,
            status=CallStatus.INITIATED.value,
            current_agent_id=initial_agent_id,
            agent_history=[initial_agent_id],
            metadata=metadata or {},
        )
        self.session.add(call)
        await self.session.flush()
        
        # Record start event
        await self.record_event(
            call.id,
            EventType.CALL_STARTED,
            data={
                "direction": direction,
                "from": from_number,
                "to": to_number,
                "agent_id": initial_agent_id,
            },
        )
        
        logger.info(
            "Created call record",
            call_id=str(call.id),
            twilio_sid=twilio_call_sid,
            direction=direction,
        )
        return call

    async def get_call_by_sid(self, twilio_call_sid: str) -> Call | None:
        """Get a call by Twilio SID."""
        stmt = select(Call).where(Call.twilio_call_sid == twilio_call_sid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_call_by_id(self, call_id: uuid.UUID) -> Call | None:
        """Get a call by ID."""
        stmt = select(Call).where(Call.id == call_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_call_status(
        self, call_id: uuid.UUID, status: CallStatus
    ) -> Call | None:
        """Update call status."""
        call = await self.get_call_by_id(call_id)
        if call:
            call.status = status.value
            
            if status == CallStatus.IN_PROGRESS:
                call.answered_at = datetime.utcnow()
                await self.record_event(call_id, EventType.CALL_ANSWERED)
            elif status in (CallStatus.COMPLETED, CallStatus.FAILED):
                call.ended_at = datetime.utcnow()
                if call.answered_at:
                    call.duration_seconds = int(
                        (call.ended_at - call.answered_at).total_seconds()
                    )
                await self.record_event(
                    call_id,
                    EventType.CALL_ENDED,
                    data={"status": status.value, "duration": call.duration_seconds},
                )
            
            await self.session.flush()
        return call

    async def update_call_agent(
        self, call_id: uuid.UUID, agent_id: str
    ) -> Call | None:
        """Update current agent and record transfer."""
        call = await self.get_call_by_id(call_id)
        if call:
            old_agent = call.current_agent_id
            call.current_agent_id = agent_id
            
            if agent_id not in call.agent_history:
                call.agent_history = call.agent_history + [agent_id]
            
            await self.record_event(
                call_id,
                EventType.AGENT_TRANSFER,
                data={"from_agent": old_agent, "to_agent": agent_id},
            )
            await self.session.flush()
        return call

    # ============ Transcripts ============

    async def add_transcript(
        self,
        call_id: uuid.UUID,
        speaker: str,
        text: str,
        is_final: bool = True,
        confidence: float | None = None,
        start_time_ms: float | None = None,
        end_time_ms: float | None = None,
    ) -> Transcript:
        """Add a transcript segment."""
        transcript = Transcript(
            call_id=call_id,
            speaker=speaker,
            text=text,
            is_final=is_final,
            confidence=confidence,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
        )
        self.session.add(transcript)
        await self.session.flush()
        
        # Record event
        event_type = EventType.ASR_FINAL if is_final else EventType.ASR_PARTIAL
        await self.record_event(
            call_id,
            event_type,
            data={
                "speaker": speaker,
                "text": text,
                "confidence": confidence,
            },
        )
        
        return transcript

    async def get_call_transcripts(self, call_id: uuid.UUID) -> list[Transcript]:
        """Get all transcripts for a call."""
        stmt = (
            select(Transcript)
            .where(Transcript.call_id == call_id, Transcript.is_final == True)
            .order_by(Transcript.timestamp)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ============ Tool Invocations ============

    async def record_tool_invocation(
        self,
        call_id: uuid.UUID,
        tool_name: str,
        agent_id: str,
        parameters: dict[str, Any],
    ) -> ToolInvocation:
        """Record the start of a tool invocation."""
        invocation = ToolInvocation(
            call_id=call_id,
            tool_name=tool_name,
            agent_id=agent_id,
            parameters=parameters,
            status="pending",
        )
        self.session.add(invocation)
        await self.session.flush()
        
        await self.record_event(
            call_id,
            EventType.TOOL_CALL_START,
            data={
                "tool_name": tool_name,
                "agent_id": agent_id,
                "parameters": parameters,
            },
        )
        
        return invocation

    async def complete_tool_invocation(
        self,
        invocation_id: uuid.UUID,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> ToolInvocation | None:
        """Record the completion of a tool invocation."""
        stmt = select(ToolInvocation).where(ToolInvocation.id == invocation_id)
        res = await self.session.execute(stmt)
        invocation = res.scalar_one_or_none()
        
        if invocation:
            invocation.completed_at = datetime.utcnow()
            invocation.duration_ms = (
                invocation.completed_at - invocation.started_at
            ).total_seconds() * 1000
            
            if error_message:
                invocation.status = "error"
                invocation.error_message = error_message
            else:
                invocation.status = "success"
                invocation.result = result
            
            await self.record_event(
                invocation.call_id,
                EventType.TOOL_CALL_END,
                data={
                    "tool_name": invocation.tool_name,
                    "status": invocation.status,
                    "duration_ms": invocation.duration_ms,
                },
                latency_ms=invocation.duration_ms,
            )
            
            await self.session.flush()
        
        return invocation

    # ============ Queries ============

    async def get_recent_calls(
        self, limit: int = 50, status: CallStatus | None = None
    ) -> list[Call]:
        """Get recent calls."""
        stmt = select(Call).order_by(Call.started_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(Call.status == status.value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_calls(self) -> list[Call]:
        """Get all active calls."""
        stmt = select(Call).where(
            Call.status.in_([CallStatus.INITIATED.value, CallStatus.IN_PROGRESS.value])
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
