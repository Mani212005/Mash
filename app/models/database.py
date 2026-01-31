"""
Mash Voice - Database Models
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.config import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""

    pass


class Call(Base):
    """Represents a phone call session."""

    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    twilio_call_sid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    
    # Call metadata
    direction: Mapped[str] = mapped_column(String(16))  # inbound, outbound
    from_number: Mapped[str] = mapped_column(String(32))
    to_number: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="initiated")  # initiated, ringing, in-progress, completed, failed
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Agent tracking
    current_agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_history: Mapped[list[str]] = mapped_column(JSON, default=list)
    
    # Metadata
    metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Relationships
    events: Mapped[list["CallEvent"]] = relationship("CallEvent", back_populates="call", lazy="selectin")
    transcripts: Mapped[list["Transcript"]] = relationship("Transcript", back_populates="call", lazy="selectin")
    
    __table_args__ = (
        Index("ix_calls_status_started", "status", "started_at"),
    )


class CallEvent(Base):
    """Represents an event during a call (for timeline/debugging)."""

    __tablename__ = "call_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), index=True)
    
    # Event details
    event_type: Mapped[str] = mapped_column(String(64))  # asr_transcript, agent_response, tool_call, agent_transfer, error
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Event data
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Performance metrics
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Relationship
    call: Mapped["Call"] = relationship("Call", back_populates="events")
    
    __table_args__ = (
        Index("ix_call_events_call_type", "call_id", "event_type"),
    )


class Transcript(Base):
    """Represents a transcript segment from ASR."""

    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), index=True)
    
    # Transcript content
    speaker: Mapped[str] = mapped_column(String(16))  # user, agent
    text: Mapped[str] = mapped_column(Text)
    is_final: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timing
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    start_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # ASR metadata
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Relationship
    call: Mapped["Call"] = relationship("Call", back_populates="transcripts")


class Agent(Base):
    """Represents an agent configuration."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Agent configuration
    agent_type: Mapped[str] = mapped_column(String(32))  # primary, specialist, handoff
    system_prompt: Mapped[str] = mapped_column(Text)
    
    # Tools and capabilities
    tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    transfer_rules: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ToolInvocation(Base):
    """Represents a tool/function call during a call."""

    __tablename__ = "tool_invocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), index=True)
    
    # Tool details
    tool_name: Mapped[str] = mapped_column(String(64))
    agent_id: Mapped[str] = mapped_column(String(64))
    
    # Invocation data
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(32))  # pending, success, error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)


# Database connection utilities
_engine = None
_session_factory = None


def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url_str,
            echo=settings.debug,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory():
    """Get or create session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db_session() -> AsyncSession:
    """Get a database session (for dependency injection)."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_database():
    """Initialize database tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
