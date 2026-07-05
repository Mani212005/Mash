"""
Mash Voice - Test Configuration
"""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.main import app
from app.models.database import ConversationState
from app.agents.base_agent import LLMResponse, ToolCall


class MockResult:
    def __init__(self, scalar):
        self._scalar = scalar
    def scalar_one_or_none(self):
        return self._scalar
    def scalars(self):
        class MockScalars:
            def __init__(self, scalar):
                self._scalar = scalar
            def all(self):
                return [self._scalar] if self._scalar else []
        return MockScalars(self._scalar)
    def all(self):
        return [(self._scalar.chat_id, self._scalar.namespace)] if self._scalar else []


class MockAsyncSession:
    db = {}

    def __init__(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def execute(self, stmt):
        chat_id = None
        namespace = None
        channel = None
        
        compiled = stmt.compile()
        params = compiled.params
        for k, v in params.items():
            if 'chat_id' in k:
                chat_id = v
            elif 'namespace' in k:
                namespace = v
            elif 'channel' in k:
                channel = v
                
        found = None
        for row in self.db.values():
            match = True
            if chat_id is not None and row.chat_id != chat_id:
                match = False
            if namespace is not None and row.namespace != namespace:
                match = False
            if channel is not None and row.channel != channel:
                match = False
            if match:
                found = row
                break
                
        return MockResult(found)

    def add(self, obj):
        key = (obj.chat_id, obj.channel)
        self.db[key] = obj

    async def delete(self, obj):
        key = (obj.chat_id, obj.channel)
        self.db.pop(key, None)

    async def commit(self):
        pass


@pytest.fixture(autouse=True)
def mock_db_session(monkeypatch):
    """Automatically mock all database session calls to prevent connection attempts."""
    session_mock = MagicMock(return_value=MockAsyncSession())
    monkeypatch.setattr("app.models.database.get_session_factory", lambda: session_mock)
    
    # Also patch state.py's internal reference if it was already imported
    monkeypatch.setattr("app.core.state.get_session_factory", lambda: session_mock)
    
    # Clear the DB state
    MockAsyncSession.db.clear()
    return session_mock


@pytest.fixture(autouse=True)
def mock_llm_client():
    """Mock the Gemini LLM client to prevent making real API calls during tests."""
    from app.agents.base_agent import GeminiProvider
    
    async def mock_generate(self, messages, system_instruction, tools=None, temperature=0.7, max_output_tokens=500):
        # Default mock response text
        return LLMResponse(
            text="Hello! I am a helpful support assistant.",
            tool_calls=[]
        )
        
    with patch.object(GeminiProvider, 'generate', mock_generate):
        yield


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
