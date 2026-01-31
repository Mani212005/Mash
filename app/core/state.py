"""
Mash Voice - State Management

Handles call state, context, and session management using Redis.
"""

import json
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from app.config import get_settings
from app.models.schemas import CallContext, ConversationTurn
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Redis key prefixes
CALL_STATE_PREFIX = "call:state:"
CALL_CONTEXT_PREFIX = "call:context:"
ACTIVE_CALLS_SET = "active_calls"

# TTL for call data (24 hours)
CALL_DATA_TTL = 86400


class StateManager:
    """Manages call state and context in Redis."""

    def __init__(self):
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.from_url(
                settings.redis_url_str,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    # ============ Call State ============

    async def create_call_state(
        self,
        call_sid: str,
        initial_agent_id: str = "primary_agent",
        metadata: dict[str, Any] | None = None,
    ) -> CallContext:
        """Create initial state for a new call."""
        r = await self._get_redis()
        
        context = CallContext(
            call_sid=call_sid,
            current_agent_id=initial_agent_id,
            conversation_history=[],
            collected_slots={},
            metadata=metadata or {},
        )
        
        # Store in Redis
        key = f"{CALL_CONTEXT_PREFIX}{call_sid}"
        await r.set(key, context.model_dump_json(), ex=CALL_DATA_TTL)
        
        # Add to active calls set
        await r.sadd(ACTIVE_CALLS_SET, call_sid)
        
        logger.info("Created call state", call_sid=call_sid, agent_id=initial_agent_id)
        return context

    async def get_call_context(self, call_sid: str) -> CallContext | None:
        """Get context for a call."""
        r = await self._get_redis()
        key = f"{CALL_CONTEXT_PREFIX}{call_sid}"
        
        data = await r.get(key)
        if data:
            return CallContext.model_validate_json(data)
        return None

    async def update_call_context(self, call_sid: str, context: CallContext) -> None:
        """Update call context."""
        r = await self._get_redis()
        key = f"{CALL_CONTEXT_PREFIX}{call_sid}"
        await r.set(key, context.model_dump_json(), ex=CALL_DATA_TTL)

    async def delete_call_state(self, call_sid: str) -> None:
        """Delete call state (when call ends)."""
        r = await self._get_redis()
        
        # Remove from active calls
        await r.srem(ACTIVE_CALLS_SET, call_sid)
        
        # Keep context for a while for debugging (don't delete immediately)
        # The TTL will handle cleanup
        logger.info("Marked call state for cleanup", call_sid=call_sid)

    # ============ Conversation History ============

    async def add_conversation_turn(
        self,
        call_sid: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a turn to the conversation history."""
        context = await self.get_call_context(call_sid)
        if not context:
            logger.warning("Cannot add turn - call context not found", call_sid=call_sid)
            return

        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )
        context.conversation_history.append(turn)
        
        # Keep only last N turns to manage memory
        max_turns = 50
        if len(context.conversation_history) > max_turns:
            context.conversation_history = context.conversation_history[-max_turns:]
        
        await self.update_call_context(call_sid, context)

    async def get_conversation_history(self, call_sid: str) -> list[ConversationTurn]:
        """Get conversation history for a call."""
        context = await self.get_call_context(call_sid)
        if context:
            return context.conversation_history
        return []

    # ============ Agent Management ============

    async def set_current_agent(self, call_sid: str, agent_id: str) -> None:
        """Set the current agent for a call."""
        context = await self.get_call_context(call_sid)
        if context:
            old_agent = context.current_agent_id
            context.current_agent_id = agent_id
            await self.update_call_context(call_sid, context)
            logger.info(
                "Agent switched",
                call_sid=call_sid,
                old_agent=old_agent,
                new_agent=agent_id,
            )

    async def get_current_agent(self, call_sid: str) -> str | None:
        """Get the current agent for a call."""
        context = await self.get_call_context(call_sid)
        if context:
            return context.current_agent_id
        return None

    # ============ Slot Collection ============

    async def set_slot(self, call_sid: str, slot_name: str, value: Any) -> None:
        """Set a collected slot value."""
        context = await self.get_call_context(call_sid)
        if context:
            context.collected_slots[slot_name] = value
            await self.update_call_context(call_sid, context)

    async def get_slot(self, call_sid: str, slot_name: str) -> Any:
        """Get a collected slot value."""
        context = await self.get_call_context(call_sid)
        if context:
            return context.collected_slots.get(slot_name)
        return None

    async def get_all_slots(self, call_sid: str) -> dict[str, Any]:
        """Get all collected slots."""
        context = await self.get_call_context(call_sid)
        if context:
            return context.collected_slots
        return {}

    # ============ Intent & Sentiment ============

    async def set_intent(self, call_sid: str, intent: str) -> None:
        """Set the detected intent."""
        context = await self.get_call_context(call_sid)
        if context:
            context.intent = intent
            await self.update_call_context(call_sid, context)

    async def set_sentiment(self, call_sid: str, sentiment: str) -> None:
        """Set the detected sentiment."""
        context = await self.get_call_context(call_sid)
        if context:
            context.sentiment = sentiment
            await self.update_call_context(call_sid, context)

    # ============ Active Calls ============

    async def get_active_calls(self) -> set[str]:
        """Get all active call SIDs."""
        r = await self._get_redis()
        return await r.smembers(ACTIVE_CALLS_SET)

    async def is_call_active(self, call_sid: str) -> bool:
        """Check if a call is active."""
        r = await self._get_redis()
        return await r.sismember(ACTIVE_CALLS_SET, call_sid)


# Singleton instance
_state_manager: StateManager | None = None


def get_state_manager() -> StateManager:
    """Get the state manager singleton."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
