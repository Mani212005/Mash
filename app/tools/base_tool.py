"""
Mash Voice - Base Tool

Abstract base class for all tools/function calls.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.utils.logging import get_logger

logger = get_logger(__name__)


class ToolResult:
    """Result of a tool execution."""

    def __init__(
        self,
        success: bool,
        data: dict[str, Any] | None = None,
        error: str | None = None,
        message: str | None = None,
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.message = message  # Human-readable message to include in response
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseTool(ABC):
    """
    Abstract base class for tools.
    
    All tools must implement:
    - execute(): Run the tool with given parameters
    """

    # Class-level attributes (override in subclasses)
    name: str = "base_tool"
    description: str = "Base tool description"
    
    # JSON Schema for parameters
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    
    # Required permissions (for access control)
    required_permissions: list[str] = []
    
    # Timeout in seconds
    timeout_seconds: float = 30.0

    def __init__(self):
        self._logger = get_logger(f"tool.{self.name}")

    @abstractmethod
    async def execute(self, **params: Any) -> ToolResult:
        """
        Execute the tool with the given parameters.
        
        Args:
            **params: Tool-specific parameters
            
        Returns:
            ToolResult with success/failure and data
        """
        pass

    def validate_params(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate parameters against the schema.
        
        Args:
            params: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required parameters
        required = self.parameters.get("required", [])
        for req in required:
            if req not in params:
                return False, f"Missing required parameter: {req}"
        
        # Basic type checking
        properties = self.parameters.get("properties", {})
        for key, value in params.items():
            if key not in properties:
                continue
            
            expected_type = properties[key].get("type")
            if expected_type:
                if expected_type == "string" and not isinstance(value, str):
                    return False, f"Parameter {key} must be a string"
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    return False, f"Parameter {key} must be a number"
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return False, f"Parameter {key} must be a boolean"
                elif expected_type == "array" and not isinstance(value, list):
                    return False, f"Parameter {key} must be an array"
                elif expected_type == "object" and not isinstance(value, dict):
                    return False, f"Parameter {key} must be an object"
        
        return True, None

    def get_definition(self) -> dict[str, Any]:
        """Get the tool definition for LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """Registry for available tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.info("Registered tool", tool=tool.name)

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_definitions(self, tool_names: list[str] | None = None) -> list[dict[str, Any]]:
        """
        Get tool definitions for LLM.
        
        Args:
            tool_names: Optional list of specific tools to include
            
        Returns:
            List of tool definitions
        """
        if tool_names is None:
            return [t.get_definition() for t in self._tools.values()]
        
        return [
            self._tools[name].get_definition()
            for name in tool_names
            if name in self._tools
        ]


# Singleton registry
_tool_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the tool registry singleton."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
