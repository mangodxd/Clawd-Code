"""
Workflow engine for enterprise automation and orchestration.

Provides:
- Workflow definition with steps and dependencies
- Execution engine with state management
- Error handling and retry logic
- Audit logging and compliance tracking
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SKIPPED = "skipped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StepResult:
    """Result of a workflow step execution."""

    step_id: str
    status: StepStatus
    output: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0.0


@dataclass
class WorkflowStep:
    """A single step in a workflow."""

    id: str
    name: str
    action: Callable[..., Any]
    dependencies: list[str] = field(default_factory=list)
    retry_count: int = 0
    retry_delay_seconds: int = 60
    timeout_seconds: int = 300
    params: dict[str, Any] = field(default_factory=dict)
    condition: Callable[[], bool] | None = None

    def should_run(self, context: dict[str, Any]) -> bool:
        """Check if step should run based on condition."""
        if self.condition is None:
            return True
        return self.condition()


@dataclass
class Workflow:
    """Workflow definition."""

    id: str
    name: str
    description: str
    steps: list[WorkflowStep]
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    timeout_seconds: int = 3600
    max_retries: int = 3

    def get_step(self, step_id: str) -> WorkflowStep | None:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_entry_points(self) -> list[WorkflowStep]:
        """Get steps with no dependencies (entry points)."""
        return [s for s in self.steps if not s.dependencies]


@dataclass
class WorkflowExecution:
    """Runtime execution state of a workflow."""

    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: datetime | None = None
    step_results: dict[str, StepResult] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "step_results": {
                k: {
                    "step_id": v.step_id,
                    "status": v.status.value,
                    "output": v.output,
                    "error": v.error,
                    "started_at": v.started_at.isoformat() if v.started_at else None,
                    "completed_at": v.completed_at.isoformat() if v.completed_at else None,
                    "duration_seconds": v.duration_seconds,
                }
                for k, v in self.step_results.items()
            },
            "context": self.context,
            "error": self.error,
        }


class WorkflowEngine:
    """Execute and manage workflows."""

    def __init__(self, storage_dir: Path | None = None):
        """
        Initialize workflow engine.

        Args:
            storage_dir: Directory for execution persistence
        """
        self.storage_dir = storage_dir or Path.home() / ".claude" / "workflows"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.workflows: dict[str, Workflow] = {}
        self.executions: dict[str, WorkflowExecution] = {}

    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow."""
        self.workflows[workflow.id] = workflow

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        """Get a registered workflow."""
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> list[Workflow]:
        """List all registered workflows."""
        return list(self.workflows.values())

    def execute(
        self,
        workflow_id: str,
        context: dict[str, Any] | None = None,
        execution_id: str | None = None,
    ) -> WorkflowExecution:
        """
        Execute a workflow.

        Args:
            workflow_id: Workflow to execute
            context: Initial context data
            execution_id: Optional execution ID (auto-generated if not provided)

        Returns:
            WorkflowExecution with results
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        execution_id = execution_id or str(uuid4())
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(),
            context=context or {},
        )

        self.executions[execution_id] = execution

        try:
            # Execute steps in dependency order
            completed_steps: set[str] = set()
            failed_steps: set[str] = set()

            while len(completed_steps) + len(failed_steps) < len(workflow.steps):
                # Find ready steps (dependencies satisfied)
                ready_steps = [
                    step
                    for step in workflow.steps
                    if step.id not in completed_steps
                    and step.id not in failed_steps
                    and all(dep in completed_steps for dep in step.dependencies)
                ]

                if not ready_steps:
                    # No more steps can run
                    break

                # Execute ready steps
                for step in ready_steps:
                    result = self._execute_step(workflow, step, execution)
                    execution.step_results[step.id] = result

                    if result.status == StepStatus.COMPLETED:
                        completed_steps.add(step.id)
                    elif result.status == StepStatus.FAILED:
                        failed_steps.add(step.id)
                    elif result.status == StepStatus.SKIPPED:
                        completed_steps.add(step.id)

            # Determine final status
            if failed_steps:
                execution.status = WorkflowStatus.FAILED
                execution.error = f"Steps failed: {', '.join(failed_steps)}"
            else:
                execution.status = WorkflowStatus.COMPLETED

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)

        finally:
            execution.completed_at = datetime.now()
            self._save_execution(execution)

        return execution

    def _execute_step(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        execution: WorkflowExecution,
    ) -> StepResult:
        """Execute a single workflow step."""
        result = StepResult(
            step_id=step.id,
            status=StepStatus.PENDING,
        )

        # Check condition
        if not step.should_run(execution.context):
            result.status = StepStatus.SKIPPED
            return result

        # Execute with retry
        for attempt in range(step.retry_count + 1):
            try:
                result.started_at = datetime.now()
                result.status = StepStatus.RUNNING

                # Execute action
                output = step.action(**step.params, context=execution.context)

                result.status = StepStatus.COMPLETED
                result.output = output
                result.completed_at = datetime.now()
                result.duration_seconds = (
                    result.completed_at - result.started_at
                ).total_seconds()

                # Update context with output
                execution.context[step.id] = output

                return result

            except Exception as e:
                result.error = str(e)
                if attempt < step.retry_count:
                    # Retry
                    import time

                    time.sleep(step.retry_delay_seconds)
                else:
                    # Final failure
                    result.status = StepStatus.FAILED
                    result.completed_at = datetime.now()
                    result.duration_seconds = (
                        result.completed_at - result.started_at
                    ).total_seconds()
                    return result

        return result

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        """Get an execution by ID."""
        return self.executions.get(execution_id)

    def list_executions(
        self,
        workflow_id: str | None = None,
        status: WorkflowStatus | None = None,
    ) -> list[WorkflowExecution]:
        """
        List executions with optional filters.

        Args:
            workflow_id: Filter by workflow
            status: Filter by status

        Returns:
            List of matching executions
        """
        results = list(self.executions.values())

        if workflow_id:
            results = [e for e in results if e.workflow_id == workflow_id]

        if status:
            results = [e for e in results if e.status == status]

        return results

    def _save_execution(self, execution: WorkflowExecution) -> None:
        """Save execution to disk."""
        execution_file = self.storage_dir / f"{execution.execution_id}.json"
        execution_file.write_text(json.dumps(execution.to_dict(), indent=2))

    def load_execution(self, execution_id: str) -> WorkflowExecution | None:
        """Load execution from disk."""
        execution_file = self.storage_dir / f"{execution_id}.json"

        if not execution_file.exists():
            return None

        data = json.loads(execution_file.read_text())

        execution = WorkflowExecution(
            execution_id=data["execution_id"],
            workflow_id=data["workflow_id"],
            status=WorkflowStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data["completed_at"]
                else None
            ),
            context=data["context"],
            error=data["error"],
        )

        # Load step results
        for step_id, step_data in data["step_results"].items():
            execution.step_results[step_id] = StepResult(
                step_id=step_data["step_id"],
                status=StepStatus(step_data["status"]),
                output=step_data["output"],
                error=step_data["error"],
                started_at=(
                    datetime.fromisoformat(step_data["started_at"])
                    if step_data["started_at"]
                    else None
                ),
                completed_at=(
                    datetime.fromisoformat(step_data["completed_at"])
                    if step_data["completed_at"]
                    else None
                ),
                duration_seconds=step_data["duration_seconds"],
            )

        self.executions[execution_id] = execution
        return execution


def create_workflow_engine(storage_dir: Path | None = None) -> WorkflowEngine:
    """Create a workflow engine instance."""
    return WorkflowEngine(storage_dir)
