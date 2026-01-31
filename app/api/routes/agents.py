"""
Mash Voice - Agent Management Routes

REST API endpoints for agent configuration.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.models import (
    Agent,
    AgentCreate,
    AgentList,
    AgentResponse,
    get_db_session,
)
from app.services import get_orchestrator
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=AgentList)
async def list_agents():
    """
    List all available agents.
    """
    orchestrator = get_orchestrator()
    agents = orchestrator._agent_registry.get_all()
    
    agent_responses = []
    for name, agent in agents.items():
        agent_responses.append(
            AgentResponse(
                id=agent.name,
                name=agent.name.replace("_", " ").title(),
                description=agent.description,
                agent_type=agent.agent_type,
                system_prompt=agent.system_prompt,
                tools=agent.tools,
                transfer_rules=agent.transfer_rules,
                is_active=True,
                config={},
                created_at=None,
                updated_at=None,
            )
        )
    
    return AgentList(agents=agent_responses)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """
    Get agent configuration by ID.
    """
    orchestrator = get_orchestrator()
    agent = orchestrator.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentResponse(
        id=agent.name,
        name=agent.name.replace("_", " ").title(),
        description=agent.description,
        agent_type=agent.agent_type,
        system_prompt=agent.system_prompt,
        tools=agent.tools,
        transfer_rules=agent.transfer_rules,
        is_active=True,
        config={},
        created_at=None,
        updated_at=None,
    )


@router.get("/{agent_id}/tools")
async def get_agent_tools(agent_id: str):
    """
    Get tools available to an agent.
    """
    orchestrator = get_orchestrator()
    agent = orchestrator.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    from app.tools import get_tool_registry
    registry = get_tool_registry()
    
    tools = []
    for tool_name in agent.tools:
        tool = registry.get(tool_name)
        if tool:
            tools.append(tool.get_definition())
    
    return {"agent_id": agent_id, "tools": tools}
