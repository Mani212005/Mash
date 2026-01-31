"""
Mash Voice - Base Agent

Abstract base class for all voice agents.
"""

from abc import ABC, abstractmethod
from datetime import datetime
import json
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.schemas import CallContext, ConversationTurn, ToolDefinition
from app.utils.logging import CallLogger, get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for voice agents.
    
    All agents must implement:
    - process(): Handle user input and generate response
    - should_transfer(): Determine if call should transfer to another agent
    """

    # Class-level attributes (override in subclasses)
    name: str = "base_agent"
    description: str = "Base agent"
    agent_type: str = "primary"  # primary, specialist, handoff
    
    # Default system prompt (override in subclasses)
    system_prompt: str = """You are a helpful voice assistant. 
    Keep responses concise and natural for spoken conversation.
    Avoid long lists or complex formatting."""
    
    # Tools available to this agent
    tools: list[str] = []
    
    # Transfer rules: {intent: target_agent_name}
    transfer_rules: dict[str, str] = {}

    def __init__(self):
        self._settings = get_settings()
        self._gemini_client = genai.Client(api_key=self._settings.gemini_api_key)

    async def process(
        self,
        user_input: str,
        context: CallContext,
        tool_definitions: list[ToolDefinition] | None = None,
    ) -> "AgentResponse":
        """
        Process user input and generate a response.
        
        Args:
            user_input: Transcribed user speech
            context: Current call context with conversation history
            tool_definitions: Available tools for function calling
            
        Returns:
            AgentResponse with text and optional tool calls
        """
        log = CallLogger(context.call_sid)
        
        try:
            # Build conversation contents for Gemini
            contents = self._build_gemini_contents(user_input, context)
            
            # Prepare tools for Gemini
            gemini_tools = None
            if tool_definitions:
                function_declarations = [
                    types.FunctionDeclaration(
                        name=t.name,
                        description=t.description,
                        parameters=t.parameters,
                    )
                    for t in tool_definitions
                ]
                gemini_tools = [types.Tool(function_declarations=function_declarations)]
            
            log.debug("Calling Gemini", content_count=len(contents))
            
            # Build config
            config = types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=500,  # Keep responses concise for voice
                system_instruction=self.system_prompt,
                tools=gemini_tools,
            )
            
            # Call Gemini
            response = await self._gemini_client.aio.models.generate_content(
                model=self._settings.gemini_model,
                contents=contents,
                config=config,
            )
            
            # Handle Gemini response
            tool_calls = []
            text = ""
            
            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if part.text:
                        text += part.text
                    elif part.function_call:
                        fc = part.function_call
                        tool_calls.append(
                            ToolCall(
                                id=f"call_{fc.name}_{len(tool_calls)}",
                                name=fc.name,
                                arguments=json.dumps(dict(fc.args)) if fc.args else "{}",
                            )
                        )
            
            if tool_calls:
                log.info(
                    "LLM requested tool calls",
                    tools=[tc.name for tc in tool_calls],
                )
            
            log.info(
                "Agent response generated",
                agent=self.name,
                response_length=len(text),
                tool_calls=len(tool_calls),
            )
            
            return AgentResponse(
                agent_id=self.name,
                text=text,
                tool_calls=tool_calls,
                context_updates={},
            )
            
        except Exception as e:
            log.exception("Error processing user input", error=str(e))
            return AgentResponse(
                agent_id=self.name,
                text="I apologize, I'm having trouble processing that. Could you please repeat?",
                tool_calls=[],
                context_updates={},
                error=str(e),
            )

    async def should_transfer(self, context: CallContext) -> str | None:
        """
        Determine if the call should be transferred to another agent.
        
        Args:
            context: Current call context
            
        Returns:
            Target agent name or None to stay with current agent
        """
        # Check transfer rules based on detected intent
        if context.intent and context.intent in self.transfer_rules:
            return self.transfer_rules[context.intent]
        
        return None

    async def get_greeting(self, context: CallContext) -> str:
        """
        Get the initial greeting for this agent.
        
        Override for custom greetings.
        """
        return "Hello! How can I help you today?"

    async def get_farewell(self, context: CallContext) -> str:
        """
        Get the farewell message for this agent.
        
        Override for custom farewells.
        """
        return "Thank you for calling. Goodbye!"

    async def handle_silence(self, context: CallContext, silence_duration_ms: float) -> str | None:
        """
        Handle when user has been silent for a while.
        
        Args:
            context: Current call context
            silence_duration_ms: How long user has been silent
            
        Returns:
            Prompt to say, or None to wait longer
        """
        if silence_duration_ms > 5000:
            return "Are you still there?"
        return None

    async def handle_error(self, context: CallContext, error: Exception) -> str:
        """
        Handle an error during processing.
        
        Args:
            context: Current call context
            error: The error that occurred
            
        Returns:
            Error message to say to user
        """
        return "I'm sorry, I encountered an issue. Let me try that again."

    def _build_gemini_contents(
        self,
        user_input: str,
        context: CallContext,
    ) -> list[types.Content]:
        """Build the content list for Gemini."""
        contents = []
        
        # Add conversation history
        for turn in context.conversation_history[-10:]:  # Last 10 turns
            role = "user" if turn.role == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=turn.content)],
                )
            )
        
        # Add current user input
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=user_input)],
            )
        )
        
        return contents

    def _build_system_prompt(self, context: CallContext) -> str:
        """Build the system prompt with context."""
        prompt = self.system_prompt
        
        # Add collected slots as context
        if context.collected_slots:
            slots_info = "\n".join(
                f"- {k}: {v}" for k, v in context.collected_slots.items()
            )
            prompt += f"\n\nCollected information:\n{slots_info}"
        
        # Add intent if detected
        if context.intent:
            prompt += f"\n\nDetected intent: {context.intent}"
        
        return prompt


class ToolCall:
    """Represents a tool call from the agent."""

    def __init__(self, id: str, name: str, arguments: str):
        self.id = id
        self.name = name
        self.arguments = arguments

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
        }


class AgentResponse:
    """Response from an agent."""

    def __init__(
        self,
        agent_id: str,
        text: str,
        tool_calls: list[ToolCall] | None = None,
        context_updates: dict[str, Any] | None = None,
        error: str | None = None,
    ):
        self.agent_id = agent_id
        self.text = text
        self.tool_calls = tool_calls or []
        self.context_updates = context_updates or {}
        self.error = error
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "text": self.text,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "context_updates": self.context_updates,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }
