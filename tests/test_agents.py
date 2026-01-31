"""
Mash Voice - Agent Tests
"""

import pytest

from app.agents import BaseAgent, PrimaryAgent, SchedulerAgent
from app.models.schemas import CallContext


@pytest.fixture
def primary_agent():
    return PrimaryAgent()


@pytest.fixture
def scheduler_agent():
    return SchedulerAgent()


@pytest.fixture
def call_context():
    return CallContext(
        call_sid="test-call-123",
        current_agent_id="primary_agent",
        conversation_history=[],
        collected_slots={},
    )


class TestPrimaryAgent:
    """Tests for the primary agent."""

    def test_agent_attributes(self, primary_agent):
        """Test agent has required attributes."""
        assert primary_agent.name == "primary_agent"
        assert primary_agent.agent_type == "primary"
        assert len(primary_agent.system_prompt) > 0
        assert isinstance(primary_agent.tools, list)

    @pytest.mark.asyncio
    async def test_greeting(self, primary_agent, call_context):
        """Test agent greeting."""
        greeting = await primary_agent.get_greeting(call_context)
        assert isinstance(greeting, str)
        assert len(greeting) > 0

    @pytest.mark.asyncio
    async def test_farewell(self, primary_agent, call_context):
        """Test agent farewell."""
        farewell = await primary_agent.get_farewell(call_context)
        assert isinstance(farewell, str)
        assert len(farewell) > 0

    @pytest.mark.asyncio
    async def test_should_transfer_no_intent(self, primary_agent, call_context):
        """Test no transfer when no intent detected."""
        target = await primary_agent.should_transfer(call_context)
        assert target is None

    @pytest.mark.asyncio
    async def test_should_transfer_booking_intent(self, primary_agent, call_context):
        """Test transfer for booking intent."""
        call_context.intent = "booking"
        target = await primary_agent.should_transfer(call_context)
        assert target == "scheduler_agent"


class TestSchedulerAgent:
    """Tests for the scheduler agent."""

    def test_agent_attributes(self, scheduler_agent):
        """Test agent has required attributes."""
        assert scheduler_agent.name == "scheduler_agent"
        assert scheduler_agent.agent_type == "specialist"
        assert "book_appointment" in scheduler_agent.tools

    @pytest.mark.asyncio
    async def test_greeting(self, scheduler_agent, call_context):
        """Test agent greeting."""
        greeting = await scheduler_agent.get_greeting(call_context)
        assert isinstance(greeting, str)
        assert "schedule" in greeting.lower() or "appointment" in greeting.lower()
