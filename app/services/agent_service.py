"""
Mash Voice - Agent Service (Orchestrator)

Manages agent lifecycle, routing, and orchestration.
"""

import asyncio
import json
from datetime import datetime
from typing import Any

from app.agents import (
    AgentResponse,
    BaseAgent,
    HumanHandoffAgent,
    PrimaryAgent, 
    SalesAgent,
    SchedulerAgent,
    SupportAgent,
)
from app.agents.customer_service_agent import CustomerServiceAgent
from app.core.state import StateManager, get_state_manager
from app.models.schemas import CallContext, ToolDefinition
from app.tools import get_tool_registry, register_all_tools
from app.utils.logging import CallLogger, get_logger

logger = get_logger(__name__)


class AgentRegistry:
    """Registry for available agents."""

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent."""
        self._agents[agent.name] = agent
        logger.info(
            "Registered agent",
            agent=agent.name,
            type=agent.agent_type,
            tools=agent.tools,
        )

    def get(self, name: str) -> BaseAgent | None:
        """Get an agent by name."""
        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    def get_all(self) -> dict[str, BaseAgent]:
        """Get all registered agents."""
        return self._agents.copy()


class AgentOrchestrator:
    """
    Orchestrates agent interactions during calls.
    
    Responsibilities:
    - Route calls to appropriate agents
    - Handle agent transfers
    - Manage conversation context
    - Execute tool calls
    """

    def __init__(self):
        self._agent_registry = AgentRegistry()
        self._state_manager = get_state_manager()
        self._tool_registry = get_tool_registry()
        
        # Register default agents
        self._register_default_agents()
        
        # Register tools
        register_all_tools()

    def _register_default_agents(self) -> None:
        """Register the default set of agents."""
        agents = [
            PrimaryAgent(),
            SchedulerAgent(),
            SupportAgent(),
            SalesAgent(),
            HumanHandoffAgent(),
            CustomerServiceAgent(),  # Customer service chatbot
        ]
        for agent in agents:
            self._agent_registry.register(agent)

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a custom agent."""
        self._agent_registry.register(agent)

    def get_agent(self, name: str) -> BaseAgent | None:
        """Get an agent by name."""
        return self._agent_registry.get(name)

    async def initialize_call(
        self,
        call_sid: str,
        initial_agent: str = "primary_agent",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Initialize a new call with the orchestrator.
        
        Args:
            call_sid: Twilio call SID
            initial_agent: Agent to start the call
            metadata: Optional call metadata
            
        Returns:
            Initial greeting from the agent
        """
        log = CallLogger(call_sid)
        
        # Create call state
        context = await self._state_manager.create_call_state(
            call_sid=call_sid,
            initial_agent_id=initial_agent,
            metadata=metadata,
        )
        
        # Get the initial agent
        agent = self._agent_registry.get(initial_agent)
        if not agent:
            agent = self._agent_registry.get("primary_agent")
        
        # Get greeting
        greeting = await agent.get_greeting(context)
        
        log.info(
            "Call initialized",
            agent=agent.name,
            greeting_length=len(greeting),
        )
        
        # Add greeting to conversation history
        await self._state_manager.add_conversation_turn(
            call_sid=call_sid,
            role="assistant",
            content=greeting,
            metadata={"agent": agent.name, "type": "greeting"},
        )
        
        return greeting

    async def process_input(
        self,
        call_sid: str,
        user_input: str,
    ) -> AgentResponse:
        """
        Process user input and generate agent response.
        
        Args:
            call_sid: Twilio call SID
            user_input: Transcribed user speech
            
        Returns:
            AgentResponse with text and any tool calls
        """
        log = CallLogger(call_sid)
        log.info("Processing user input", input_length=len(user_input))
        
        # Get current context
        context = await self._state_manager.get_call_context(call_sid)
        if not context:
            log.error("Call context not found")
            return AgentResponse(
                agent_id="unknown",
                text="I'm sorry, there was an error. Could you please call back?",
                error="Context not found",
            )
        
        # Add user input to history
        await self._state_manager.add_conversation_turn(
            call_sid=call_sid,
            role="user",
            content=user_input,
        )
        
        # Get current agent
        agent = self._agent_registry.get(context.current_agent_id)
        if not agent:
            log.warning("Agent not found, using primary", agent=context.current_agent_id)
            agent = self._agent_registry.get("primary_agent")
        
        # Get tool definitions for this agent
        tool_definitions = self._get_agent_tools(agent)
        
        # Process with agent
        response = await agent.process(
            user_input=user_input,
            context=context,
            tool_definitions=tool_definitions,
        )
        
        # Handle tool calls
        if response.tool_calls:
            response = await self._handle_tool_calls(
                call_sid=call_sid,
                response=response,
                context=context,
            )
        
        # Check for agent transfer
        updated_context = await self._state_manager.get_call_context(call_sid)
        if updated_context:
            transfer_target = await agent.should_transfer(updated_context)
            if transfer_target:
                response = await self._handle_agent_transfer(
                    call_sid=call_sid,
                    from_agent=agent.name,
                    to_agent=transfer_target,
                    context=updated_context,
                )
        
        # Add response to history
        await self._state_manager.add_conversation_turn(
            call_sid=call_sid,
            role="assistant",
            content=response.text,
            metadata={"agent": response.agent_id},
        )
        
        log.info(
            "Generated response",
            agent=response.agent_id,
            response_length=len(response.text),
            tool_calls=len(response.tool_calls),
        )
        
        return response

    async def end_call(self, call_sid: str) -> str:
        """
        End a call and get farewell message.
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            Farewell message from the agent
        """
        log = CallLogger(call_sid)
        
        context = await self._state_manager.get_call_context(call_sid)
        if not context:
            return "Goodbye!"
        
        agent = self._agent_registry.get(context.current_agent_id)
        if not agent:
            agent = self._agent_registry.get("primary_agent")
        
        farewell = await agent.get_farewell(context)
        
        # Clean up state
        await self._state_manager.delete_call_state(call_sid)
        
        log.info("Call ended", agent=agent.name)
        
        return farewell

    async def transfer_agent(
        self,
        call_sid: str,
        target_agent: str,
        reason: str | None = None,
    ) -> AgentResponse:
        """
        Explicitly transfer to a different agent.
        
        Args:
            call_sid: Twilio call SID
            target_agent: Name of agent to transfer to
            reason: Optional reason for transfer
            
        Returns:
            Response from the new agent
        """
        context = await self._state_manager.get_call_context(call_sid)
        if not context:
            return AgentResponse(
                agent_id="unknown",
                text="I'm sorry, there was an error with the transfer.",
                error="Context not found",
            )
        
        return await self._handle_agent_transfer(
            call_sid=call_sid,
            from_agent=context.current_agent_id,
            to_agent=target_agent,
            context=context,
        )

    def _get_agent_tools(self, agent: BaseAgent) -> list[ToolDefinition]:
        """Get tool definitions for an agent."""
        tool_definitions = []
        for tool_name in agent.tools:
            tool = self._tool_registry.get(tool_name)
            if tool:
                defn = tool.get_definition()
                tool_definitions.append(
                    ToolDefinition(
                        name=defn["name"],
                        description=defn["description"],
                        parameters=defn["parameters"],
                    )
                )
        return tool_definitions

    async def _handle_tool_calls(
        self,
        call_sid: str,
        response: AgentResponse,
        context: CallContext,
    ) -> AgentResponse:
        """Execute tool calls and get updated response."""
        log = CallLogger(call_sid)
        
        tool_results = []
        for tool_call in response.tool_calls:
            log.info(
                "Executing tool",
                tool=tool_call.name,
                call_id=tool_call.id,
            )
            
            tool = self._tool_registry.get(tool_call.name)
            if not tool:
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "error": f"Tool '{tool_call.name}' not found",
                })
                continue
            
            try:
                # Parse arguments
                args = json.loads(tool_call.arguments)
                
                # Execute tool
                result = await tool.execute(**args)
                
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "name": tool_call.name,
                    "result": result.to_dict(),
                })
                
                # If tool has a message, update response
                if result.message:
                    response.text = result.message
                
                log.info(
                    "Tool executed",
                    tool=tool_call.name,
                    success=result.success,
                )
                
            except json.JSONDecodeError as e:
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "error": f"Invalid arguments: {e}",
                })
            except Exception as e:
                log.exception("Tool execution failed", tool=tool_call.name, error=str(e))
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "error": str(e),
                })
        
        return response

    async def _handle_agent_transfer(
        self,
        call_sid: str,
        from_agent: str,
        to_agent: str,
        context: CallContext,
    ) -> AgentResponse:
        """Handle transfer between agents."""
        log = CallLogger(call_sid)
        
        target = self._agent_registry.get(to_agent)
        if not target:
            log.warning("Transfer target not found", target=to_agent)
            return AgentResponse(
                agent_id=from_agent,
                text="I apologize, I'm unable to transfer you at the moment.",
                error=f"Agent '{to_agent}' not found",
            )
        
        # Update context
        await self._state_manager.set_current_agent(call_sid, to_agent)
        
        # Get updated context
        updated_context = await self._state_manager.get_call_context(call_sid)
        
        # Get greeting from new agent
        greeting = await target.get_greeting(updated_context or context)
        
        log.info(
            "Agent transfer complete",
            from_agent=from_agent,
            to_agent=to_agent,
        )
        
        return AgentResponse(
            agent_id=to_agent,
            text=greeting,
            context_updates={"transferred_from": from_agent},
        )

    async def process_message(
        self,
        session_id: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process a message and return the response.
        
        Simplified interface for WhatsApp integration.
        
        Args:
            session_id: Session identifier
            message: User message text
            context: Optional context dict
            
        Returns:
            Response dict with message, agent, options, etc.
        """
        try:
            # Get or create call context
            call_context = await self._state_manager.get_call_context(session_id)
            
            if not call_context:
                # Initialize new session
                await self._state_manager.create_call_state(
                    call_sid=session_id,
                    initial_agent_id="primary_agent",
                    metadata=context,
                )
                call_context = await self._state_manager.get_call_context(session_id)
            
            # Process through the agent
            response = await self.process_input(
                call_sid=session_id,
                user_input=message,
            )
            
            return {
                "message": response.text,
                "agent": response.agent_id,
                "tool_calls": [tc.model_dump() for tc in response.tool_calls] if response.tool_calls else [],
                "transfer_to": response.transfer_to,
                "context_update": response.context_updates,
                "options": None,  # Can be extended to provide button options
                "next_agent": response.transfer_to,
            }
            
        except Exception as e:
            logger.exception("Error processing message", error=str(e))
            return {
                "message": "I apologize, but I encountered an error. Please try again.",
                "agent": "primary_agent",
                "error": str(e),
            }


# Singleton instance
_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    """Get the agent orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


# Alias for convenience
def get_agent_orchestrator() -> AgentOrchestrator:
    """Get the agent orchestrator singleton (alias)."""
    return get_orchestrator()
