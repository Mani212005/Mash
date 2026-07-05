"""
Mash Voice - API Tests
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Mash Voice Platform"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient):
    """Test listing agents."""
    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert len(data["agents"]) > 0

    # Check primary agent exists
    agent_names = [a["id"] for a in data["agents"]]
    assert "primary_agent" in agent_names


@pytest.mark.asyncio
async def test_get_agent(client: AsyncClient):
    """Test getting a specific agent."""
    response = await client.get("/api/v1/agents/primary_agent")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "primary_agent"
    assert "system_prompt" in data
    assert "tools" in data


@pytest.mark.asyncio
async def test_get_nonexistent_agent(client: AsyncClient):
    """Test getting a nonexistent agent."""
    response = await client.get("/api/v1/agents/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_stats(client: AsyncClient):
    """Test dashboard stats endpoint with mocked StateManager."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from datetime import datetime

    mock_sm = MagicMock()
    mock_redis = AsyncMock()

    # Mock some keys
    mock_redis.keys.return_value = ["conversation:1", "conversation:2"]

    # Mock data for key 1 and 2
    # Ensure date matches today UTC for messages_today calculation
    today_str = datetime.utcnow().date().isoformat() + "T12:00:00"

    mock_redis.hgetall.side_effect = [
        {
            b"status": b"active",
            b"last_message_at": today_str.encode(),
            b"message_count": b"5",
            b"avg_response_time_ms": b"120.0",
        },
        {
            b"status": b"escalated",
            b"last_message_at": today_str.encode(),
            b"message_count": b"10",
            b"avg_response_time_ms": b"240.0",
        },
    ]

    mock_sm.redis = mock_redis

    # Patch get_state_manager in the dashboard route module
    with patch("app.api.routes.dashboard.get_state_manager", return_value=mock_sm):
        response = await client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_conversations"] == 2
        assert data["active_conversations"] == 1
        assert data["messages_today"] == 15
        assert data["avg_response_time_ms"] == 180.0
        assert data["escalation_rate"] == 0.5

