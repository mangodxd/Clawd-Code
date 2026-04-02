"""Tests for job_scheduler module."""

import unittest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from src.job_scheduler import (
    JobStatus,
    JobDefinition,
    JobExecution,
    JobScheduler,
    create_job_scheduler,
)


class TestJobScheduler(unittest.TestCase):
    """Test cases for job scheduler."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.test_dir)

    def test_create_job_definition(self):
        """Test creating a job definition."""
        job = JobDefinition(
            id="job1",
            name="Test Job",
            schedule="daily at 9:00",
            action=lambda: "result",
        )

        self.assertEqual(job.id, "job1")
        self.assertEqual(job.name, "Test Job")
        self.assertTrue(job.enabled)

    def test_create_job_execution(self):
        """Test creating a job execution."""
        execution = JobExecution(
            execution_id="exec1",
            job_id="job1",
            status=JobStatus.RUNNING,
            scheduled_time=datetime.now(),
        )

        self.assertEqual(execution.execution_id, "exec1")
        self.assertEqual(execution.status, JobStatus.RUNNING)

    def test_execution_to_dict(self):
        """Test execution serialization."""
        execution = JobExecution(
            execution_id="exec1",
            job_id="job1",
            status=JobStatus.COMPLETED,
            scheduled_time=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

        data = execution.to_dict()

        self.assertEqual(data["execution_id"], "exec1")
        self.assertEqual(data["status"], "completed")

    def test_create_job_scheduler(self):
        """Test creating a job scheduler."""
        scheduler = create_job_scheduler(self.test_dir)

        self.assertIsInstance(scheduler, JobScheduler)
        self.assertEqual(scheduler.storage_dir, self.test_dir)

    def test_schedule_job(self):
        """Test scheduling a job."""
        scheduler = create_job_scheduler(self.test_dir)

        job = scheduler.schedule_job(
            name="Test Job",
            schedule="daily at 9:00",
            action=lambda: "result",
        )

        self.assertIsNotNone(job.id)
        self.assertEqual(job.name, "Test Job")
        self.assertIn(job.id, scheduler.jobs)

    def test_schedule_job_with_id(self):
        """Test scheduling job with specific ID."""
        scheduler = create_job_scheduler(self.test_dir)

        job = scheduler.schedule_job(
            name="Test Job",
            schedule="daily at 9:00",
            action=lambda: "result",
            job_id="custom-id",
        )

        self.assertEqual(job.id, "custom-id")

    def test_get_job(self):
        """Test getting a scheduled job."""
        scheduler = create_job_scheduler(self.test_dir)

        job = scheduler.schedule_job(
            name="Test Job",
            schedule="daily at 9:00",
            action=lambda: "result",
            job_id="job1",
        )

        found = scheduler.get_job("job1")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Test Job")

    def test_list_jobs(self):
        """Test listing jobs."""
        scheduler = create_job_scheduler(self.test_dir)

        scheduler.schedule_job(
            name="Job 1",
            schedule="daily at 9:00",
            action=lambda: None,
        )

        scheduler.schedule_job(
            name="Job 2",
            schedule="hourly",
            action=lambda: None,
        )

        jobs = scheduler.list_jobs()
        self.assertEqual(len(jobs), 2)

    def test_list_jobs_enabled_only(self):
        """Test listing only enabled jobs."""
        scheduler = create_job_scheduler(self.test_dir)

        scheduler.schedule_job(
            name="Job 1",
            schedule="daily at 9:00",
            action=lambda: None,
        )

        job2 = scheduler.schedule_job(
            name="Job 2",
            schedule="hourly",
            action=lambda: None,
        )

        scheduler.pause_job(job2.id)

        jobs = scheduler.list_jobs(enabled_only=True)
        self.assertEqual(len(jobs), 1)

    def test_update_job(self):
        """Test updating a job."""
        scheduler = create_job_scheduler(self.test_dir)

        job = scheduler.schedule_job(
            name="Original Name",
            schedule="hourly",
            action=lambda: None,
        )

        updated = scheduler.update_job(job.id, name="New Name")

        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, "New Name")

    def test_pause_job(self):
        """Test pausing a job."""
        scheduler = create_job_scheduler(self.test_dir)

        job = scheduler.schedule_job(
            name="Test Job",
            schedule="hourly",
            action=lambda: None,
        )

        scheduler.pause_job(job.id)

        paused = scheduler.get_job(job.id)
        self.assertFalse(paused.enabled)

    def test_resume_job(self):
        """Test resuming a paused job."""
        scheduler = create_job_scheduler(self.test_dir)

        job = scheduler.schedule_job(
            name="Test Job",
            schedule="hourly",
            action=lambda: None,
        )

        scheduler.pause_job(job.id)
        scheduler.resume_job(job.id)

        resumed = scheduler.get_job(job.id)
        self.assertTrue(resumed.enabled)

    def test_cancel_job(self):
        """Test canceling a job."""
        scheduler = create_job_scheduler(self.test_dir)

        job = scheduler.schedule_job(
            name="Test Job",
            schedule="hourly",
            action=lambda: None,
        )

        result = scheduler.cancel_job(job.id)

        self.assertTrue(result)
        self.assertIsNone(scheduler.get_job(job.id))

    def test_execute_job(self):
        """Test executing a job."""
        scheduler = create_job_scheduler(self.test_dir)

        execution_result = []

        job = scheduler.schedule_job(
            name="Test Job",
            schedule="hourly",
            action=lambda: execution_result.append("executed"),
        )

        execution = scheduler.execute_job(job.id)

        self.assertEqual(execution.status, JobStatus.COMPLETED)
        self.assertIn("executed", execution_result)

    def test_execute_job_with_failure(self):
        """Test executing a job that fails."""
        scheduler = create_job_scheduler(self.test_dir)

        job = scheduler.schedule_job(
            name="Failing Job",
            schedule="hourly",
            action=lambda: 1 / 0,  # ZeroDivisionError
            max_retries=0,
        )

        execution = scheduler.execute_job(job.id)

        self.assertEqual(execution.status, JobStatus.FAILED)
        self.assertIsNotNone(execution.error)

    def test_execute_job_with_retry(self):
        """Test job execution with retry."""
        scheduler = create_job_scheduler(self.test_dir)

        attempt_count = []

        def failing_action():
            attempt_count.append(1)
            if len(attempt_count) < 2:
                raise ValueError("Not yet")
            return "success"

        job = scheduler.schedule_job(
            name="Retry Job",
            schedule="hourly",
            action=failing_action,
            max_retries=2,
            retry_delay_seconds=0,  # No delay for tests
        )

        execution = scheduler.execute_job(job.id)

        self.assertEqual(execution.status, JobStatus.COMPLETED)
        self.assertEqual(len(attempt_count), 2)

    def test_get_execution(self):
        """Test getting an execution."""
        scheduler = create_job_scheduler(self.test_dir)

        job = scheduler.schedule_job(
            name="Test Job",
            schedule="hourly",
            action=lambda: None,
        )

        execution = scheduler.execute_job(job.id)

        found = scheduler.get_execution(execution.execution_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.execution_id, execution.execution_id)

    def test_list_executions(self):
        """Test listing executions."""
        scheduler = create_job_scheduler(self.test_dir)

        job = scheduler.schedule_job(
            name="Test Job",
            schedule="hourly",
            action=lambda: None,
        )

        scheduler.execute_job(job.id)
        scheduler.execute_job(job.id)

        executions = scheduler.list_executions()
        self.assertEqual(len(executions), 2)

    def test_list_executions_by_job(self):
        """Test listing executions filtered by job."""
        scheduler = create_job_scheduler(self.test_dir)

        job1 = scheduler.schedule_job(
            name="Job 1",
            schedule="hourly",
            action=lambda: None,
        )

        job2 = scheduler.schedule_job(
            name="Job 2",
            schedule="hourly",
            action=lambda: None,
        )

        scheduler.execute_job(job1.id)
        scheduler.execute_job(job2.id)

        executions = scheduler.list_executions(job_id=job1.id)
        self.assertEqual(len(executions), 1)

    def test_list_executions_by_status(self):
        """Test listing executions filtered by status."""
        scheduler = create_job_scheduler(self.test_dir)

        job1 = scheduler.schedule_job(
            name="Success Job",
            schedule="hourly",
            action=lambda: None,
        )

        job2 = scheduler.schedule_job(
            name="Fail Job",
            schedule="hourly",
            action=lambda: 1 / 0,
            max_retries=0,
        )

        scheduler.execute_job(job1.id)
        scheduler.execute_job(job2.id)

        completed = scheduler.list_executions(status=JobStatus.COMPLETED)
        failed = scheduler.list_executions(status=JobStatus.FAILED)

        self.assertEqual(len(completed), 1)
        self.assertEqual(len(failed), 1)

    def test_job_persistence(self):
        """Test saving and loading job."""
        scheduler = create_job_scheduler(self.test_dir)

        job = scheduler.schedule_job(
            name="Test Job",
            schedule="hourly",
            action=lambda: None,
            tags=["important"],
        )

        # Load job
        loaded = scheduler.load_job(job.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Test Job")
        self.assertIn("important", loaded.tags)

    def test_execution_persistence(self):
        """Test execution is saved to disk."""
        scheduler = create_job_scheduler(self.test_dir)

        job = scheduler.schedule_job(
            name="Test Job",
            schedule="hourly",
            action=lambda: "result",
        )

        execution = scheduler.execute_job(job.id)

        # Check file exists
        exec_file = self.test_dir / f"exec_{execution.execution_id}.json"
        self.assertTrue(exec_file.exists())


if __name__ == "__main__":
    unittest.main()
