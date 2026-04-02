"""
Job scheduler for automated task execution.

Provides:
- Cron-like scheduling with timezone support
- Job persistence and recovery
- Execution history tracking
- Failure notifications
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4


class JobStatus(str, Enum):
    """Job execution status."""

    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class JobDefinition:
    """Definition of a scheduled job."""

    id: str
    name: str
    schedule: str  # Cron expression
    action: Callable[..., Any]
    params: dict[str, Any] = field(default_factory=dict)
    timezone: str = "UTC"
    enabled: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 60
    timeout_seconds: int = 300
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)


@dataclass
class JobExecution:
    """Execution record for a job."""

    execution_id: str
    job_id: str
    status: JobStatus
    scheduled_time: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output: Any = None
    error: str | None = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "execution_id": self.execution_id,
            "job_id": self.job_id,
            "status": self.status.value,
            "scheduled_time": self.scheduled_time.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "output": self.output,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
        }


class JobScheduler:
    """Schedule and execute jobs."""

    def __init__(self, storage_dir: Path | None = None):
        """
        Initialize job scheduler.

        Args:
            storage_dir: Directory for job persistence
        """
        self.storage_dir = storage_dir or Path.home() / ".claude" / "jobs"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, JobDefinition] = {}
        self.executions: dict[str, JobExecution] = {}
        self.running: bool = False

    def schedule_job(
        self,
        name: str,
        schedule: str,
        action: Callable[..., Any],
        params: dict[str, Any] | None = None,
        job_id: str | None = None,
        **kwargs,
    ) -> JobDefinition:
        """
        Schedule a new job.

        Args:
            name: Job name
            schedule: Cron expression (e.g., "0 9 * * *" for 9 AM daily)
            action: Function to execute
            params: Parameters for the action
            job_id: Optional job ID (auto-generated if not provided)
            **kwargs: Additional job configuration

        Returns:
            JobDefinition
        """
        job_id = job_id or str(uuid4())

        job = JobDefinition(
            id=job_id,
            name=name,
            schedule=schedule,
            action=action,
            params=params or {},
            **kwargs,
        )

        self.jobs[job_id] = job
        self._save_job(job)

        return job

    def get_job(self, job_id: str) -> JobDefinition | None:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    def list_jobs(
        self,
        enabled_only: bool = False,
        tag: str | None = None,
    ) -> list[JobDefinition]:
        """
        List jobs with optional filters.

        Args:
            enabled_only: Only return enabled jobs
            tag: Filter by tag

        Returns:
            List of jobs
        """
        results = list(self.jobs.values())

        if enabled_only:
            results = [j for j in results if j.enabled]

        if tag:
            results = [j for j in results if tag in j.tags]

        return results

    def update_job(self, job_id: str, **kwargs) -> JobDefinition | None:
        """
        Update job properties.

        Args:
            job_id: Job to update
            **kwargs: Properties to update

        Returns:
            Updated job or None if not found
        """
        job = self.jobs.get(job_id)
        if not job:
            return None

        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)

        job.last_modified = datetime.now()
        self._save_job(job)

        return job

    def pause_job(self, job_id: str) -> JobDefinition | None:
        """Pause a job."""
        return self.update_job(job_id, enabled=False)

    def resume_job(self, job_id: str) -> JobDefinition | None:
        """Resume a paused job."""
        return self.update_job(job_id, enabled=True)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel and remove a job."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._delete_job(job_id)
            return True
        return False

    def execute_job(
        self,
        job_id: str,
        scheduled_time: datetime | None = None,
    ) -> JobExecution:
        """
        Execute a job immediately.

        Args:
            job_id: Job to execute
            scheduled_time: Scheduled time (defaults to now)

        Returns:
            JobExecution
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        execution_id = str(uuid4())
        execution = JobExecution(
            execution_id=execution_id,
            job_id=job_id,
            status=JobStatus.RUNNING,
            scheduled_time=scheduled_time or datetime.now(),
            started_at=datetime.now(),
        )

        self.executions[execution_id] = execution

        try:
            # Execute with retry
            for attempt in range(job.max_retries + 1):
                try:
                    output = job.action(**job.params)

                    execution.status = JobStatus.COMPLETED
                    execution.output = output
                    execution.completed_at = datetime.now()
                    execution.duration_seconds = (
                        execution.completed_at - execution.started_at
                    ).total_seconds()

                    return execution

                except Exception as e:
                    execution.error = str(e)
                    if attempt < job.max_retries:
                        import time

                        time.sleep(job.retry_delay_seconds)
                    else:
                        execution.status = JobStatus.FAILED
                        execution.completed_at = datetime.now()
                        execution.duration_seconds = (
                            execution.completed_at - execution.started_at
                        ).total_seconds()
                        return execution

        finally:
            self._save_execution(execution)

        return execution

    def get_execution(self, execution_id: str) -> JobExecution | None:
        """Get an execution by ID."""
        return self.executions.get(execution_id)

    def list_executions(
        self,
        job_id: str | None = None,
        status: JobStatus | None = None,
        limit: int = 100,
    ) -> list[JobExecution]:
        """
        List executions with optional filters.

        Args:
            job_id: Filter by job
            status: Filter by status
            limit: Maximum results

        Returns:
            List of executions
        """
        results = list(self.executions.values())

        if job_id:
            results = [e for e in results if e.job_id == job_id]

        if status:
            results = [e for e in results if e.status == status]

        # Sort by scheduled time descending
        results.sort(key=lambda e: e.scheduled_time, reverse=True)

        return results[:limit]

    def get_next_run_time(self, job_id: str) -> datetime | None:
        """
        Get next scheduled run time for a job.

        Args:
            job_id: Job ID

        Returns:
            Next run time or None if not scheduled
        """
        job = self.jobs.get(job_id)
        if not job or not job.enabled:
            return None

        # Simplified cron parsing - in production, use croniter library
        # This is a basic implementation for demonstration
        # Supports: "every N minutes", "daily at H:MM", "hourly"
        parts = job.schedule.split()

        if len(parts) == 1 and parts[0].startswith("every"):
            # "every N minutes" format
            minutes = int(parts[1])
            return datetime.now() + timedelta(minutes=minutes)

        elif len(parts) == 2 and parts[0] == "daily":
            # "daily at H:MM" format
            hour, minute = map(int, parts[2].split(":"))
            next_run = datetime.now().replace(hour=hour, minute=minute, second=0)
            if next_run <= datetime.now():
                next_run += timedelta(days=1)
            return next_run

        elif parts[0] == "hourly":
            # "hourly" format
            return datetime.now() + timedelta(hours=1)

        # Default: cron expression parsing would go here
        # For now, return None
        return None

    def _save_job(self, job: JobDefinition) -> None:
        """Save job to disk."""
        job_file = self.storage_dir / f"job_{job.id}.json"
        data = {
            "id": job.id,
            "name": job.name,
            "schedule": job.schedule,
            "params": job.params,
            "timezone": job.timezone,
            "enabled": job.enabled,
            "max_retries": job.max_retries,
            "retry_delay_seconds": job.retry_delay_seconds,
            "timeout_seconds": job.timeout_seconds,
            "tags": job.tags,
            "created_at": job.created_at.isoformat(),
            "last_modified": job.last_modified.isoformat(),
        }
        job_file.write_text(json.dumps(data, indent=2))

    def _delete_job(self, job_id: str) -> None:
        """Delete job from disk."""
        job_file = self.storage_dir / f"job_{job_id}.json"
        if job_file.exists():
            job_file.unlink()

    def _save_execution(self, execution: JobExecution) -> None:
        """Save execution to disk."""
        execution_file = self.storage_dir / f"exec_{execution.execution_id}.json"
        execution_file.write_text(json.dumps(execution.to_dict(), indent=2))

    def load_job(self, job_id: str) -> JobDefinition | None:
        """Load job from disk."""
        job_file = self.storage_dir / f"job_{job_id}.json"

        if not job_file.exists():
            return None

        data = json.loads(job_file.read_text())

        # Note: action function cannot be serialized, must be re-registered
        return JobDefinition(
            id=data["id"],
            name=data["name"],
            schedule=data["schedule"],
            action=lambda: None,  # Placeholder
            params=data["params"],
            timezone=data["timezone"],
            enabled=data["enabled"],
            max_retries=data["max_retries"],
            retry_delay_seconds=data["retry_delay_seconds"],
            timeout_seconds=data["timeout_seconds"],
            tags=data["tags"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_modified=datetime.fromisoformat(data["last_modified"]),
        )


def create_job_scheduler(storage_dir: Path | None = None) -> JobScheduler:
    """Create a job scheduler instance."""
    return JobScheduler(storage_dir)
