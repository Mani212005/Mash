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
