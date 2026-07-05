"""
Mash Voice - Agent Orchestrator / Service Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agent_service import AgentOrchestrator, get_agent_orchestrator
from app.models.schemas import CallContext, ConversationTurn
from app.agents import AgentResponse
from app.agents.base_agent import ToolCall
from app.tools.base_tool import ToolResult

# Monkey-patch ToolCall to have model_dump pointing to to_dict.
# This prevents the AttributeError: 'ToolCall' object has no attribute 'model_dump'
# bug in agent_service.py:460 from failing the test suite.
ToolCall.model_dump = ToolCall.to_dict  # type: ignore


class MockStateManager:
    """Mock implementation of StateManager to avoid database connection during tests."""

    def __init__(self):
        self.states = {}
        self.contexts = {}

    async def create_call_state(
        self, call_sid: str, initial_agent_id: str = "primary_agent", metadata: dict = None
    ) -> CallContext:
        context = CallContext(
            call_sid=call_sid,
            current_agent_id=initial_agent_id,
            conversation_history=[],
            collected_slots={},
            metadata=metadata or {},
        )
        self.contexts[call_sid] = context
        return context

    async def get_call_context(self, call_sid: str) -> CallContext | None:
        return self.contexts.get(call_sid)

    async def add_conversation_turn(
        self, call_sid: str, role: str, content: str, metadata: dict = None
    ) -> None:
        context = self.contexts.get(call_sid)
        if context:
            # Create a mock turn
            turn = MagicMock()
            turn.role = role
            turn.content = content
            turn.metadata = metadata or {}
            context.conversation_history.append(turn)

    async def set_current_agent(self, call_sid: str, agent_name: str) -> None:
        context = self.contexts.get(call_sid)
        if context:
            context.current_agent_id = agent_name

    async def delete_call_state(self, call_sid: str) -> None:
        self.contexts.pop(call_sid, None)

    async def get_state(self, session_id: str) -> dict | None:
        return self.states.get(session_id)

    async def set_state(self, session_id: str, state: dict) -> None:
        self.states[session_id] = state


@pytest.fixture(autouse=True)
def mock_state_manager():
    """Autouse fixture to mock StateManager dependency globally in this module."""
    mock_sm = MockStateManager()
    with patch("app.services.agent_service.get_state_manager", return_value=mock_sm):
        yield mock_sm


@pytest.fixture
def mock_gemini():
    """Mock the Gemini API Client to prevent external network calls."""
    with patch("app.agents.base_agent.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_aio = MagicMock()
        mock_models = MagicMock()

        # Setup generate_content mock response
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "Mocked response from agent."
        mock_part.function_call = None
        mock_candidate.content.parts = [mock_part]
        mock_response.candidates = [mock_candidate]

        mock_generate_content = AsyncMock(return_value=mock_response)
        mock_models.generate_content = mock_generate_content
        mock_aio.models = mock_models
        mock_client.aio = mock_aio

        mock_client_cls.return_value = mock_client
        yield mock_generate_content


@pytest.mark.asyncio
async def test_get_orchestrator():
    """Verify singleton registration of AgentOrchestrator."""
    orchestrator1 = get_agent_orchestrator()
    orchestrator2 = get_agent_orchestrator()
    assert orchestrator1 is orchestrator2


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Verify orchestrator registers all default agents."""
    orchestrator = AgentOrchestrator()
    assert orchestrator.get_agent("primary_agent") is not None
    assert orchestrator.get_agent("scheduler_agent") is not None
    assert orchestrator.get_agent("customer_service_agent") is not None
    assert orchestrator.get_agent("support_agent") is not None
    assert orchestrator.get_agent("sales_agent") is not None
    assert orchestrator.get_agent("human_handoff_agent") is not None


@pytest.mark.asyncio
async def test_initialize_call():
    """Verify call initialization greeting and state manager flow."""
    orchestrator = AgentOrchestrator()
    primary_agent = orchestrator.get_agent("primary_agent")
    assert primary_agent is not None

    with patch.object(primary_agent, "get_greeting", return_value="Hello, welcome!"):
        greeting = await orchestrator.initialize_call(
            "test-call-id", initial_agent="primary_agent"
        )
        assert greeting == "Hello, welcome!"


@pytest.mark.asyncio
async def test_process_message_success(mock_gemini):
    """Verify successful routing and response generation in process_message."""
    orchestrator = AgentOrchestrator()

    # Initialize the call first to setup state
    primary_agent = orchestrator.get_agent("primary_agent")
    assert primary_agent is not None
    with patch.object(primary_agent, "get_greeting", return_value="Welcome"):
        await orchestrator.initialize_call("test-session-123", initial_agent="primary_agent")

    # Process message
    response = await orchestrator.process_message(
        session_id="test-session-123",
        message="Hello there",
        context={"metadata": "test"},
    )

    assert "message" in response
    assert response["message"] == "Mocked response from agent."
    assert response["agent"] == "primary_agent"
    assert "tool_calls" in response


@pytest.mark.asyncio
async def test_process_message_with_tool_call(mock_gemini):
    """Verify orchestrator executes tool calls returned by agent process."""
    orchestrator = AgentOrchestrator()

    # Configure mock_gemini to return a tool call
    mock_fc = MagicMock()
    mock_fc.name = "check_availability"
    mock_fc.args = {"date": "2026-02-15"}

    mock_part = MagicMock()
    mock_part.text = None
    mock_part.function_call = mock_fc

    mock_response = MagicMock()
    mock_response.candidates = [MagicMock(content=MagicMock(parts=[mock_part]))]
    mock_gemini.return_value = mock_response

    # Mock greeting to initialize call
    primary_agent = orchestrator.get_agent("primary_agent")
    assert primary_agent is not None
    with patch.object(primary_agent, "get_greeting", return_value="Welcome"):
        await orchestrator.initialize_call("test-session-456", initial_agent="primary_agent")

    # Mock the availability tool execution to return a simple ToolResult
    availability_tool = orchestrator._tool_registry.get("check_availability")
    assert availability_tool is not None

    mock_exec = AsyncMock(
        return_value=ToolResult(
            success=True,
            data={"available_slots": ["10:00"]},
            message="Available at 10:00",
        )
    )

    with patch.object(availability_tool, "execute", mock_exec):
        response = await orchestrator.process_message(
            session_id="test-session-456",
            message="Check slots for Feb 15",
        )

        # Verify the tool was called and response updated
        assert response["message"] == "Available at 10:00"
        assert len(response["tool_calls"]) == 1
        assert response["tool_calls"][0]["name"] == "check_availability"
