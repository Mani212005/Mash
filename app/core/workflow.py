"""
Mash Voice - Workflow Engine

Handles step-based execution, conditional branching, and retry logic.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Awaitable

from app.utils.logging import get_logger

logger = get_logger(__name__)


class StepStatus(str, Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of executing a workflow step."""
    status: StepStatus
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0


@dataclass
class WorkflowStep:
    """Definition of a workflow step."""
    name: str
    handler: Callable[..., Awaitable[StepResult]]
    condition: Callable[[dict[str, Any]], bool] | None = None
    retry_count: int = 0
    retry_delay_ms: int = 1000
    timeout_seconds: float = 30.0
    on_failure: str | None = None  # Step to jump to on failure


@dataclass
class WorkflowExecution:
    """Tracks the execution state of a workflow."""
    workflow_name: str
    call_sid: str
    current_step: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    step_results: dict[str, StepResult] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class Workflow:
    """
    A workflow is a sequence of steps that are executed in order.
    
    Each step can have:
    - A condition (to skip if not met)
    - Retry logic
    - A failure handler (jump to another step)
    """

    def __init__(self, name: str):
        self.name = name
        self.steps: list[WorkflowStep] = []
        self._step_map: dict[str, int] = {}

    def add_step(
        self,
        name: str,
        handler: Callable[..., Awaitable[StepResult]],
        condition: Callable[[dict[str, Any]], bool] | None = None,
        retry_count: int = 0,
        retry_delay_ms: int = 1000,
        timeout_seconds: float = 30.0,
        on_failure: str | None = None,
    ) -> "Workflow":
        """Add a step to the workflow."""
        step = WorkflowStep(
            name=name,
            handler=handler,
            condition=condition,
            retry_count=retry_count,
            retry_delay_ms=retry_delay_ms,
            timeout_seconds=timeout_seconds,
            on_failure=on_failure,
        )
        self._step_map[name] = len(self.steps)
        self.steps.append(step)
        return self

    async def execute(
        self,
        call_sid: str,
        initial_context: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        """Execute the workflow."""
        execution = WorkflowExecution(
            workflow_name=self.name,
            call_sid=call_sid,
            context=initial_context or {},
        )
        execution.status = StepStatus.RUNNING
        
        logger.info(
            "Starting workflow",
            workflow=self.name,
            call_sid=call_sid,
            steps=len(self.steps),
        )

        try:
            while execution.current_step < len(self.steps):
                step = self.steps[execution.current_step]
                
                # Check condition
                if step.condition and not step.condition(execution.context):
                    logger.debug(
                        "Skipping step (condition not met)",
                        workflow=self.name,
                        step=step.name,
                    )
                    execution.step_results[step.name] = StepResult(
                        status=StepStatus.SKIPPED
                    )
                    execution.current_step += 1
                    continue
                
                # Execute step with retries
                result = await self._execute_step(step, execution)
                execution.step_results[step.name] = result
                
                # Handle failure
                if result.status == StepStatus.FAILED:
                    if step.on_failure and step.on_failure in self._step_map:
                        # Jump to failure handler step
                        execution.current_step = self._step_map[step.on_failure]
                        logger.info(
                            "Jumping to failure handler",
                            workflow=self.name,
                            from_step=step.name,
                            to_step=step.on_failure,
                        )
                        continue
                    else:
                        # No failure handler, abort workflow
                        execution.status = StepStatus.FAILED
                        break
                
                # Update context with step result data
                execution.context.update(result.data)
                execution.current_step += 1
            
            if execution.status != StepStatus.FAILED:
                execution.status = StepStatus.COMPLETED
            
        except Exception as e:
            logger.exception(
                "Workflow execution failed",
                workflow=self.name,
                call_sid=call_sid,
                error=str(e),
            )
            execution.status = StepStatus.FAILED
        
        execution.completed_at = datetime.utcnow()
        
        logger.info(
            "Workflow completed",
            workflow=self.name,
            call_sid=call_sid,
            status=execution.status.value,
            duration_ms=(execution.completed_at - execution.started_at).total_seconds() * 1000,
        )
        
        return execution

    async def _execute_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
    ) -> StepResult:
        """Execute a single step with retry logic."""
        attempts = 0
        max_attempts = step.retry_count + 1
        last_error = None
        
        while attempts < max_attempts:
            attempts += 1
            start_time = datetime.utcnow()
            
            try:
                logger.debug(
                    "Executing step",
                    workflow=self.name,
                    step=step.name,
                    attempt=attempts,
                )
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    step.handler(execution.context, execution.call_sid),
                    timeout=step.timeout_seconds,
                )
                
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                result.duration_ms = duration_ms
                
                if result.status == StepStatus.COMPLETED:
                    logger.info(
                        "Step completed",
                        workflow=self.name,
                        step=step.name,
                        duration_ms=duration_ms,
                    )
                    return result
                
                last_error = result.error
                
            except asyncio.TimeoutError:
                last_error = f"Step timed out after {step.timeout_seconds}s"
                logger.warning(
                    "Step timeout",
                    workflow=self.name,
                    step=step.name,
                    timeout=step.timeout_seconds,
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Step failed",
                    workflow=self.name,
                    step=step.name,
                    error=str(e),
                    attempt=attempts,
                )
            
            # Retry delay
            if attempts < max_attempts:
                await asyncio.sleep(step.retry_delay_ms / 1000)
        
        return StepResult(
            status=StepStatus.FAILED,
            error=last_error or "Unknown error",
        )


class WorkflowRegistry:
    """Registry for workflow definitions."""

    def __init__(self):
        self._workflows: dict[str, Workflow] = {}

    def register(self, workflow: Workflow) -> None:
        """Register a workflow."""
        self._workflows[workflow.name] = workflow
        logger.info("Registered workflow", workflow=workflow.name)

    def get(self, name: str) -> Workflow | None:
        """Get a workflow by name."""
        return self._workflows.get(name)

    def list_workflows(self) -> list[str]:
        """List all registered workflow names."""
        return list(self._workflows.keys())


# Singleton registry
_workflow_registry: WorkflowRegistry | None = None


def get_workflow_registry() -> WorkflowRegistry:
    """Get the workflow registry singleton."""
    global _workflow_registry
    if _workflow_registry is None:
        _workflow_registry = WorkflowRegistry()
    return _workflow_registry


# ============ Common Workflow Steps ============

async def identify_intent_step(context: dict[str, Any], call_sid: str) -> StepResult:
    """Step to identify user intent from transcript."""
    # This would typically call an LLM to identify intent
    transcript = context.get("last_transcript", "")
    
    # Placeholder - in real implementation, use LLM
    intent = "unknown"
    if any(word in transcript.lower() for word in ["book", "schedule", "appointment"]):
        intent = "booking"
    elif any(word in transcript.lower() for word in ["help", "support", "issue", "problem"]):
        intent = "support"
    elif any(word in transcript.lower() for word in ["cancel", "stop"]):
        intent = "cancellation"
    
    return StepResult(
        status=StepStatus.COMPLETED,
        data={"intent": intent},
    )


async def validate_slots_step(context: dict[str, Any], call_sid: str) -> StepResult:
    """Step to validate collected slots."""
    required_slots = context.get("required_slots", [])
    collected_slots = context.get("collected_slots", {})
    
    missing_slots = [s for s in required_slots if s not in collected_slots]
    
    if missing_slots:
        return StepResult(
            status=StepStatus.FAILED,
            error=f"Missing slots: {missing_slots}",
            data={"missing_slots": missing_slots},
        )
    
    return StepResult(
        status=StepStatus.COMPLETED,
        data={"validation": "passed"},
    )


# Example workflow
def create_booking_workflow() -> Workflow:
    """Create a booking workflow."""
    workflow = Workflow("booking")
    
    workflow.add_step(
        name="identify_intent",
        handler=identify_intent_step,
    )
    
    workflow.add_step(
        name="validate_slots",
        handler=validate_slots_step,
        condition=lambda ctx: ctx.get("intent") == "booking",
        retry_count=2,
    )
    
    return workflow
