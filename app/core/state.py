"""
Mash Voice - State Management

Handles call state, context, and session management using PostgreSQL (replacing Redis).
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Set

from sqlalchemy import select

from app.models.database import ConversationState, get_session_factory
from app.models.schemas import CallContext, ConversationTurn
from app.utils.logging import get_logger

logger = get_logger(__name__)

# TTL for call data (24 hours) - maintained for logic, though Postgres-only does not automatically expire rows
CALL_DATA_TTL = 86400


def _resolve_key(key: str) -> tuple[str, str]:
    """Helper to map a Redis key to (chat_id, namespace) for PostgreSQL."""
    if key.startswith("call:context:"):
        return key.replace("call:context:", "", 1), "call"
    elif key.startswith("call:state:"):
        return key.replace("call:state:", "", 1), "call"
    elif key.startswith("session:state:"):
        return key.replace("session:state:", "", 1), "whatsapp"
    else:
        return key, "redis_compat"


def _reconstruct_key(chat_id: str, namespace: str) -> str:
    """Helper to reconstruct a Redis key from PostgreSQL fields."""
    if namespace == "call":
        return f"call:context:{chat_id}"
    elif namespace == "whatsapp":
        return f"session:state:{chat_id}"
    else:
        return chat_id


class FakeRedis:
    """
    Compatibility layer that translates Redis operations used by the application
    into PostgreSQL queries against the ConversationState model.
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def get(self, key: str) -> str | None:
        chat_id, namespace = _resolve_key(key)
        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == chat_id, ConversationState.namespace == namespace
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                if namespace == "call":
                    slots_data = row.slots or {}
                    collected_slots = slots_data.get("collected_slots", {})
                    intent = slots_data.get("intent")
                    sentiment = slots_data.get("sentiment")
                    metadata = slots_data.get("metadata", {})

                    history_turns = [ConversationTurn(**t) for t in (row.history or [])]
                    context = CallContext(
                        call_sid=chat_id,
                        current_agent_id=row.current_agent or "primary_agent",
                        conversation_history=history_turns,
                        collected_slots=collected_slots,
                        intent=intent,
                        sentiment=sentiment,
                        metadata=metadata,
                    )
                    return context.model_dump_json()
                elif namespace == "whatsapp" or namespace == "generic":
                    if row.slots and "_raw_state" in row.slots:
                        return json.dumps(row.slots["_raw_state"])
                    return json.dumps(
                        {
                            "chat_id": row.chat_id,
                            "channel": row.channel,
                            "current_agent": row.current_agent,
                            "slots": row.slots,
                            "history": row.history,
                        }
                    )
                else:
                    return row.slots.get("value") if row.slots else None
        return None

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        chat_id, namespace = _resolve_key(key)
        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == chat_id, ConversationState.namespace == namespace
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if namespace == "call":
                context_dict = json.loads(value)
                current_agent = context_dict.get("current_agent_id")
                slots = {
                    "collected_slots": context_dict.get("collected_slots", {}),
                    "intent": context_dict.get("intent"),
                    "sentiment": context_dict.get("sentiment"),
                    "metadata": context_dict.get("metadata", {}),
                }
                history = context_dict.get("conversation_history", [])

                if row:
                    row.current_agent = current_agent
                    row.slots = slots
                    row.history = history
                else:
                    row = ConversationState(
                        chat_id=chat_id,
                        namespace=namespace,
                        channel=None,  # Leave free
                        current_agent=current_agent,
                        slots=slots,
                        history=history,
                    )
                    session.add(row)
            elif namespace == "whatsapp" or namespace == "generic":
                state = json.loads(value)
                current_agent = state.get("current_agent") or state.get("current_agent_id")
                slots = state.get("slots") or state.get("collected_slots") or {}
                history = state.get("history") or state.get("conversation_history") or []

                if row:
                    row.current_agent = current_agent
                    row.slots = slots if isinstance(slots, dict) else {"data": slots}
                    row.history = history
                    row.slots["_raw_state"] = state
                else:
                    row = ConversationState(
                        chat_id=chat_id,
                        namespace=namespace,
                        channel="whatsapp",  # WhatsApp channel value
                        current_agent=current_agent,
                        slots=slots if isinstance(slots, dict) else {"data": slots},
                        history=history,
                    )
                    row.slots["_raw_state"] = state
                    session.add(row)
            else:
                if row:
                    row.slots = {"value": value}
                else:
                    row = ConversationState(
                        chat_id=chat_id,
                        namespace=namespace,
                        channel=None,
                        slots={"value": value},
                        history=[],
                    )
                    session.add(row)
            await session.commit()

    async def delete(self, *keys: str) -> None:
        if not keys:
            return
        async with self._session_factory() as session:
            for key in keys:
                chat_id, namespace = _resolve_key(key)
                stmt = select(ConversationState).where(
                    ConversationState.chat_id == chat_id, ConversationState.namespace == namespace
                )
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                if row:
                    await session.delete(row)
            await session.commit()

    async def expire(self, key: str, time: int) -> None:
        pass

    async def sadd(self, key: str, *members: str) -> None:
        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == key, ConversationState.namespace == "redis_compat"
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                current_members = set(row.slots.get("members", []))
                current_members.update(members)
                row.slots = {"members": list(current_members)}
            else:
                row = ConversationState(
                    chat_id=key,
                    namespace="redis_compat",
                    channel=None,
                    slots={"members": list(members)},
                    history=[],
                )
                session.add(row)
            await session.commit()

    async def srem(self, key: str, *members: str) -> None:
        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == key, ConversationState.namespace == "redis_compat"
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                current_members = set(row.slots.get("members", []))
                current_members.difference_update(members)
                row.slots = {"members": list(current_members)}
                await session.commit()

    async def smembers(self, key: str) -> Set[str]:
        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == key, ConversationState.namespace == "redis_compat"
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row and row.slots:
                return set(row.slots.get("members", []))
        return set()

    async def sismember(self, key: str, member: str) -> bool:
        members = await self.smembers(key)
        return member in members

    async def hset(self, key: str, mapping: Dict[str, str]) -> None:
        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == key, ConversationState.namespace == "redis_compat"
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                current_hash = row.slots.get("hash", {})
                current_hash.update(mapping)
                row.slots = {"hash": current_hash}
            else:
                row = ConversationState(
                    chat_id=key,
                    namespace="redis_compat",
                    channel=None,
                    slots={"hash": mapping},
                    history=[],
                )
                session.add(row)
            await session.commit()

    async def hgetall(self, key: str) -> Dict[str, str]:
        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == key, ConversationState.namespace == "redis_compat"
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row and row.slots:
                return row.slots.get("hash", {})
        return {}

    async def keys(self, pattern: str) -> List[str]:
        sql_pattern = pattern.replace("*", "%")
        namespace = None
        if pattern.startswith("call:context:"):
            namespace = "call"
            sql_pattern = pattern.replace("call:context:", "", 1).replace("*", "%")
        elif pattern.startswith("session:state:"):
            namespace = "whatsapp"
            sql_pattern = pattern.replace("session:state:", "", 1).replace("*", "%")
        elif pattern.startswith("ticket:"):
            namespace = "redis_compat"

        async with self._session_factory() as session:
            stmt = select(ConversationState.chat_id, ConversationState.namespace).where(
                ConversationState.chat_id.like(sql_pattern)
            )
            if namespace:
                stmt = stmt.where(ConversationState.namespace == namespace)
            result = await session.execute(stmt)
            rows = result.all()
            return [_reconstruct_key(row[0], row[1]) for row in rows]

    def scan_iter(self, match: str):
        class AsyncDatabaseScanIterator:
            def __init__(self, session_factory, match_pattern):
                self._session_factory = session_factory
                self._match_pattern = match_pattern
                self._keys = None
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._keys is None:
                    namespace = None
                    sql_pattern = self._match_pattern.replace("*", "%")
                    if self._match_pattern.startswith("call:context:"):
                        namespace = "call"
                        sql_pattern = self._match_pattern.replace("call:context:", "", 1).replace(
                            "*", "%"
                        )
                    elif self._match_pattern.startswith("session:state:"):
                        namespace = "whatsapp"
                        sql_pattern = self._match_pattern.replace("session:state:", "", 1).replace(
                            "*", "%"
                        )
                    elif self._match_pattern.startswith("conversation:"):
                        namespace = "redis_compat"

                    async with self._session_factory() as session:
                        stmt = select(ConversationState.chat_id, ConversationState.namespace).where(
                            ConversationState.chat_id.like(sql_pattern)
                        )
                        if namespace:
                            stmt = stmt.where(ConversationState.namespace == namespace)
                        result = await session.execute(stmt)
                        rows = result.all()
                        self._keys = [_reconstruct_key(row[0], row[1]) for row in rows]

                if self._index >= len(self._keys):
                    raise StopAsyncIteration
                val = self._keys[self._index]
                self._index += 1
                return val

        return AsyncDatabaseScanIterator(self._session_factory, match)

    async def close(self):
        pass


class StateManager:
    """Manages call state and context in PostgreSQL."""

    def __init__(self):
        self._session_factory = get_session_factory()
        self.redis = FakeRedis(self._session_factory)

    async def _get_redis(self) -> FakeRedis:
        """Get database-backed Redis compatibility client."""
        return self.redis

    async def close(self):
        """Close database connection."""
        pass

    # ============ Call State ============

    async def create_call_state(
        self,
        call_sid: str,
        initial_agent_id: str = "primary_agent",
        metadata: dict[str, Any] | None = None,
    ) -> CallContext:
        """Create initial state for a new call."""
        context = CallContext(
            call_sid=call_sid,
            current_agent_id=initial_agent_id,
            conversation_history=[],
            collected_slots={},
            metadata=metadata or {},
        )

        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == call_sid, ConversationState.namespace == "call"
            )
            result = await session.execute(stmt)
            state = result.scalar_one_or_none()

            if not state:
                state = ConversationState(
                    chat_id=call_sid,
                    namespace="call",
                    channel=None,
                    current_agent=initial_agent_id,
                    slots={},
                    history=[],
                )
                session.add(state)
            else:
                state.current_agent = initial_agent_id
                state.slots = {}
                state.history = []

            await session.commit()

        logger.info("Created call state", call_sid=call_sid, agent_id=initial_agent_id)
        return context

    async def get_call_context(self, call_sid: str) -> CallContext | None:
        """Get context for a call."""
        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == call_sid, ConversationState.namespace == "call"
            )
            result = await session.execute(stmt)
            state = result.scalar_one_or_none()

            if state:
                slots_data = state.slots or {}
                collected_slots = slots_data.get("collected_slots", {})
                intent = slots_data.get("intent")
                sentiment = slots_data.get("sentiment")
                metadata = slots_data.get("metadata", {})

                history_turns = [ConversationTurn(**t) for t in (state.history or [])]

                return CallContext(
                    call_sid=call_sid,
                    current_agent_id=state.current_agent or "primary_agent",
                    conversation_history=history_turns,
                    collected_slots=collected_slots,
                    intent=intent,
                    sentiment=sentiment,
                    metadata=metadata,
                )
        return None

    async def update_call_context(self, call_sid: str, context: CallContext) -> None:
        """Update call context."""
        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == call_sid, ConversationState.namespace == "call"
            )
            result = await session.execute(stmt)
            state = result.scalar_one_or_none()

            slots = {
                "collected_slots": context.collected_slots,
                "intent": context.intent,
                "sentiment": context.sentiment,
                "metadata": context.metadata,
            }
            history = [turn.model_dump() for turn in context.conversation_history]

            if state:
                state.current_agent = context.current_agent_id
                state.slots = slots
                state.history = history
            else:
                state = ConversationState(
                    chat_id=call_sid,
                    namespace="call",
                    channel=None,
                    current_agent=context.current_agent_id,
                    slots=slots,
                    history=history,
                )
                session.add(state)
            await session.commit()

    async def delete_call_state(self, call_sid: str) -> None:
        """Delete call state (when call ends)."""
        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == call_sid, ConversationState.namespace == "call"
            )
            result = await session.execute(stmt)
            state = result.scalar_one_or_none()
            if state:
                await session.delete(state)
                await session.commit()
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

        max_turns = 50
        if len(context.conversation_history) > max_turns:
            context.conversation_history = context.conversation_history[-max_turns:]

        await self.update_call_context(call_sid, context)

    async def get_conversation_history(self, call_sid: str) -> List[ConversationTurn]:
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

    async def get_active_calls(self) -> Set[str]:
        """Get all active call SIDs."""
        async with self._session_factory() as session:
            stmt = select(ConversationState.chat_id).where(ConversationState.namespace == "call")
            result = await session.execute(stmt)
            return set(result.scalars().all())

    async def is_call_active(self, call_sid: str) -> bool:
        """Check if a call is active."""
        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == call_sid, ConversationState.namespace == "call"
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    # ============ Generic State (for non-call sessions) ============

    async def get_state(self, session_id: str) -> dict[str, Any] | None:
        """Get generic state for a session (e.g., WhatsApp conversation)."""
        namespace = "generic"
        chat_id = session_id
        if ":" in session_id:
            parts = session_id.split(":", 1)
            namespace = parts[0]
            chat_id = parts[1]

        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == chat_id, ConversationState.namespace == namespace
            )
            result = await session.execute(stmt)
            state_row = result.scalar_one_or_none()
            if state_row:
                if "_raw_state" in state_row.slots:
                    return state_row.slots["_raw_state"]
                return {
                    "chat_id": state_row.chat_id,
                    "channel": state_row.channel,
                    "current_agent": state_row.current_agent,
                    "slots": state_row.slots,
                    "history": state_row.history,
                }
        return None

    async def set_state(self, session_id: str, state: dict[str, Any]) -> None:
        """Set generic state for a session."""
        namespace = "generic"
        chat_id = session_id
        if ":" in session_id:
            parts = session_id.split(":", 1)
            namespace = parts[0]
            chat_id = parts[1]

        current_agent = state.get("current_agent") or state.get("current_agent_id")
        slots = state.get("slots") or state.get("collected_slots") or {}
        history = state.get("history") or state.get("conversation_history") or []

        async with self._session_factory() as session:
            stmt = select(ConversationState).where(
                ConversationState.chat_id == chat_id, ConversationState.namespace == namespace
            )
            result = await session.execute(stmt)
            state_row = result.scalar_one_or_none()

            serialized_history = []
            for item in history:
                if isinstance(item, dict):
                    serialized_history.append(item)
                else:
                    try:
                        serialized_history.append(item.model_dump())
                    except AttributeError:
                        serialized_history.append(dict(item))

            channel_val = namespace if namespace in ("whatsapp", "telegram") else None

            if state_row:
                state_row.current_agent = current_agent
                state_row.slots = slots if isinstance(slots, dict) else {"data": slots}
                state_row.history = serialized_history
                state_row.slots["_raw_state"] = state
                if channel_val:
                    state_row.channel = channel_val
            else:
                state_row = ConversationState(
                    chat_id=chat_id,
                    namespace=namespace,
                    channel=channel_val,
                    current_agent=current_agent,
                    slots=slots if isinstance(slots, dict) else {"data": slots},
                    history=serialized_history,
                )
                state_row.slots["_raw_state"] = state
                session.add(state_row)

            await session.commit()
        logger.debug("Set session state", session_id=session_id)


# Singleton instance
_state_manager: StateManager | None = None


def get_state_manager() -> StateManager:
    """Get the state manager singleton."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
