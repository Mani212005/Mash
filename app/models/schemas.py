"""
Mash Voice - Pydantic Schemas
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============ Enums ============


class CallDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(str, Enum):
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no-answer"
    BUSY = "busy"
    CANCELED = "canceled"


class EventType(str, Enum):
    CALL_STARTED = "call_started"
    CALL_ANSWERED = "call_answered"
    CALL_ENDED = "call_ended"
    ASR_PARTIAL = "asr_partial"
    ASR_FINAL = "asr_final"
    AGENT_THINKING = "agent_thinking"
    AGENT_RESPONSE = "agent_response"
    AGENT_TRANSFER = "agent_transfer"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    TTS_START = "tts_start"
    TTS_END = "tts_end"
    ERROR = "error"


class AgentType(str, Enum):
    PRIMARY = "primary"
    SPECIALIST = "specialist"
    HANDOFF = "handoff"


class Speaker(str, Enum):
    USER = "user"
    AGENT = "agent"


# ============ Call Schemas ============


class CallCreate(BaseModel):
    """Schema for creating an outbound call."""

    to_number: str = Field(..., description="Destination phone number (E.164 format)")
    from_number: str | None = Field(None, description="Source phone number (defaults to configured)")
    agent_id: str = Field(default="primary_agent", description="Initial agent to handle the call")
    metadata: dict[str, Any] = Field(default_factory=dict)


class CallResponse(BaseModel):
    """Schema for call response."""

    id: UUID
    twilio_call_sid: str
    direction: CallDirection
    from_number: str
    to_number: str
    status: CallStatus
    started_at: datetime
    answered_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    current_agent_id: str | None = None
    agent_history: list[str] = []
    metadata: dict[str, Any] = {}

    class Config:
        from_attributes = True


class CallList(BaseModel):
    """Schema for list of calls."""

    calls: list[CallResponse]
    total: int
    page: int
    page_size: int


# ============ Event Schemas ============


class CallEventCreate(BaseModel):
    """Schema for creating a call event."""

    event_type: EventType
    data: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float | None = None


class CallEventResponse(BaseModel):
    """Schema for call event response."""

    id: UUID
    call_id: UUID
    event_type: EventType
    timestamp: datetime
    data: dict[str, Any]
    latency_ms: float | None = None

    class Config:
        from_attributes = True


class CallTimeline(BaseModel):
    """Schema for call timeline view."""

    call_id: UUID
    events: list[CallEventResponse]
    duration_ms: float | None = None


# ============ Transcript Schemas ============


class TranscriptSegment(BaseModel):
    """Schema for a transcript segment."""

    speaker: Speaker
    text: str
    is_final: bool = True
    timestamp: datetime
    start_time_ms: float | None = None
    end_time_ms: float | None = None
    confidence: float | None = None


class CallTranscript(BaseModel):
    """Schema for full call transcript."""

    call_id: UUID
    segments: list[TranscriptSegment]


# ============ Agent Schemas ============


class TransferRule(BaseModel):
    """Schema for agent transfer rule."""

    target_agent: str
    conditions: dict[str, Any] = Field(default_factory=dict)
    priority: int = 0


class AgentCreate(BaseModel):
    """Schema for creating/updating an agent."""

    id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$", description="Agent identifier")
    name: str
    description: str | None = None
    agent_type: AgentType
    system_prompt: str
    tools: list[str] = Field(default_factory=list)
    transfer_rules: dict[str, TransferRule] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Schema for agent response."""

    id: str
    name: str
    description: str | None
    agent_type: AgentType
    system_prompt: str
    tools: list[str]
    transfer_rules: dict[str, Any]
    is_active: bool
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentList(BaseModel):
    """Schema for list of agents."""

    agents: list[AgentResponse]


# ============ Tool Schemas ============


class ToolParameter(BaseModel):
    """Schema for tool parameter definition."""

    type: str
    description: str
    required: bool = False
    enum: list[str] | None = None
    default: Any = None


class ToolDefinition(BaseModel):
    """Schema for tool definition."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema format


class ToolInvocationResponse(BaseModel):
    """Schema for tool invocation response."""

    id: UUID
    call_id: UUID
    tool_name: str
    agent_id: str
    parameters: dict[str, Any]
    result: dict[str, Any] | None
    status: str
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    duration_ms: float | None

    class Config:
        from_attributes = True


# ============ WebSocket Message Schemas ============


class WSMessage(BaseModel):
    """Base WebSocket message schema."""

    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class WSTranscriptMessage(WSMessage):
    """WebSocket message for transcript updates."""

    type: str = "transcript"
    data: dict[str, Any] = Field(default_factory=dict)
    # data contains: speaker, text, is_final, confidence


class WSAgentMessage(WSMessage):
    """WebSocket message for agent responses."""

    type: str = "agent_response"
    data: dict[str, Any] = Field(default_factory=dict)
    # data contains: agent_id, text, is_speaking


class WSEventMessage(WSMessage):
    """WebSocket message for call events."""

    type: str = "event"
    data: dict[str, Any] = Field(default_factory=dict)
    # data contains: event_type, details


# ============ State Schemas ============


class ConversationTurn(BaseModel):
    """Schema for a conversation turn."""

    role: str  # user, assistant, system, tool
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CallContext(BaseModel):
    """Schema for call context/state."""

    call_sid: str
    current_agent_id: str
    conversation_history: list[ConversationTurn] = Field(default_factory=list)
    collected_slots: dict[str, Any] = Field(default_factory=dict)
    intent: str | None = None
    sentiment: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============ Health & Status Schemas ============


class HealthCheck(BaseModel):
    """Schema for health check response."""

    status: str
    version: str
    services: dict[str, str]
