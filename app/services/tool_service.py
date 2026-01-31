"""
Mash Voice - Tool Executor Service

Handles tool validation, execution, and error handling.
"""

import asyncio
import json
from datetime import datetime
from typing import Any
import uuid

from app.tools import get_tool_registry, BaseTool, ToolResult
from app.utils.logging import CallLogger, get_logger

logger = get_logger(__name__)


class ToolExecutor:
    """
    Executes tools with validation, permissions, and error handling.
    """

    def __init__(self):
        self._tool_registry = get_tool_registry()

    async def execute(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        call_sid: str | None = None,
        agent_id: str | None = None,
    ) -> ToolResult:
        """
        Execute a tool with full validation and error handling.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            call_sid: Optional call SID for logging
            agent_id: Optional agent ID for tracking
            
        Returns:
            ToolResult with success/failure and data
        """
        log = CallLogger(call_sid) if call_sid else logger
        start_time = datetime.utcnow()
        
        # Get tool
        tool = self._tool_registry.get(tool_name)
        if not tool:
            log.error("Tool not found", tool=tool_name)
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found",
            )
        
        # Validate parameters
        is_valid, error = tool.validate_params(parameters)
        if not is_valid:
            log.error("Parameter validation failed", tool=tool_name, error=error)
            return ToolResult(
                success=False,
                error=error,
            )
        
        # Execute with timeout
        try:
            log.info(
                "Executing tool",
                tool=tool_name,
                timeout=tool.timeout_seconds,
            )
            
            result = await asyncio.wait_for(
                tool.execute(**parameters),
                timeout=tool.timeout_seconds,
            )
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            log.info(
                "Tool execution complete",
                tool=tool_name,
                success=result.success,
                duration_ms=duration_ms,
            )
            
            return result
            
        except asyncio.TimeoutError:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            log.error(
                "Tool execution timeout",
                tool=tool_name,
                timeout=tool.timeout_seconds,
                duration_ms=duration_ms,
            )
            return ToolResult(
                success=False,
                error=f"Tool execution timed out after {tool.timeout_seconds} seconds",
            )
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            log.exception(
                "Tool execution failed",
                tool=tool_name,
                error=str(e),
                duration_ms=duration_ms,
            )
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}",
            )

    async def execute_batch(
        self,
        tool_calls: list[dict[str, Any]],
        call_sid: str | None = None,
        parallel: bool = False,
    ) -> list[ToolResult]:
        """
        Execute multiple tools.
        
        Args:
            tool_calls: List of tool call specs with name and parameters
            call_sid: Optional call SID for logging
            parallel: Whether to execute tools in parallel
            
        Returns:
            List of ToolResults
        """
        if parallel:
            tasks = [
                self.execute(
                    tool_name=tc["name"],
                    parameters=tc.get("parameters", {}),
                    call_sid=call_sid,
                )
                for tc in tool_calls
            ]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for tc in tool_calls:
                result = await self.execute(
                    tool_name=tc["name"],
                    parameters=tc.get("parameters", {}),
                    call_sid=call_sid,
                )
                results.append(result)
            return results

    def get_available_tools(self, agent_tools: list[str] | None = None) -> list[dict[str, Any]]:
        """
        Get available tool definitions.
        
        Args:
            agent_tools: Optional list of tool names to filter by
            
        Returns:
            List of tool definitions
        """
        return self._tool_registry.get_definitions(agent_tools)

    def validate_tool_call(
        self,
        tool_name: str,
        arguments: str,
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        """
        Validate a tool call from LLM output.
        
        Args:
            tool_name: Name of the tool
            arguments: JSON string of arguments
            
        Returns:
            Tuple of (is_valid, parsed_args, error_message)
        """
        # Check tool exists
        tool = self._tool_registry.get(tool_name)
        if not tool:
            return False, None, f"Tool '{tool_name}' not found"
        
        # Parse arguments
        try:
            params = json.loads(arguments)
        except json.JSONDecodeError as e:
            return False, None, f"Invalid JSON arguments: {e}"
        
        # Validate parameters
        is_valid, error = tool.validate_params(params)
        if not is_valid:
            return False, None, error
        
        return True, params, None


# Singleton instance
_tool_executor: ToolExecutor | None = None


def get_tool_executor() -> ToolExecutor:
    """Get the tool executor singleton."""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor
