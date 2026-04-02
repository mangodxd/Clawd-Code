"""Tests for workflow_engine module."""

import unittest
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from src.workflow_engine import (
    WorkflowStatus,
    StepStatus,
    StepResult,
    WorkflowStep,
    Workflow,
    WorkflowExecution,
    WorkflowEngine,
    create_workflow_engine,
)


class TestWorkflowEngine(unittest.TestCase):
    """Test cases for workflow engine."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.test_dir)

    def test_create_step_result(self):
        """Test creating a step result."""
        result = StepResult(
            step_id="step1",
            status=StepStatus.COMPLETED,
            output={"key": "value"},
        )

        self.assertEqual(result.step_id, "step1")
        self.assertEqual(result.status, StepStatus.COMPLETED)
        self.assertEqual(result.output, {"key": "value"})

    def test_create_workflow_step(self):
        """Test creating a workflow step."""
        step = WorkflowStep(
            id="step1",
            name="Test Step",
            action=lambda: "result",
        )

        self.assertEqual(step.id, "step1")
        self.assertEqual(step.name, "Test Step")
        self.assertTrue(step.should_run({}))

    def test_create_workflow_step_with_condition(self):
        """Test step with condition."""
        step = WorkflowStep(
            id="step1",
            name="Conditional Step",
            action=lambda: "result",
            condition=lambda: False,
        )

        self.assertFalse(step.should_run({}))

    def test_create_workflow(self):
        """Test creating a workflow."""
        steps = [
            WorkflowStep(id="step1", name="Step 1", action=lambda: "result1"),
            WorkflowStep(id="step2", name="Step 2", action=lambda: "result2"),
        ]

        workflow = Workflow(
            id="wf1",
            name="Test Workflow",
            description="Test description",
            steps=steps,
        )

        self.assertEqual(workflow.id, "wf1")
        self.assertEqual(len(workflow.steps), 2)

    def test_workflow_get_step(self):
        """Test getting a step from workflow."""
        step1 = WorkflowStep(id="step1", name="Step 1", action=lambda: "result1")
        workflow = Workflow(
            id="wf1",
            name="Test Workflow",
            description="Test",
            steps=[step1],
        )

        found = workflow.get_step("step1")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Step 1")

        not_found = workflow.get_step("nonexistent")
        self.assertIsNone(not_found)

    def test_workflow_entry_points(self):
        """Test finding entry point steps."""
        step1 = WorkflowStep(id="step1", name="Step 1", action=lambda: "result1")
        step2 = WorkflowStep(
            id="step2",
            name="Step 2",
            action=lambda: "result2",
            dependencies=["step1"],
        )

        workflow = Workflow(
            id="wf1",
            name="Test",
            description="Test",
            steps=[step1, step2],
        )

        entry_points = workflow.get_entry_points()
        self.assertEqual(len(entry_points), 1)
        self.assertEqual(entry_points[0].id, "step1")

    def test_create_workflow_execution(self):
        """Test creating a workflow execution."""
        execution = WorkflowExecution(
            execution_id="exec1",
            workflow_id="wf1",
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(),
        )

        self.assertEqual(execution.execution_id, "exec1")
        self.assertEqual(execution.status, WorkflowStatus.RUNNING)

    def test_execution_to_dict(self):
        """Test execution serialization."""
        execution = WorkflowExecution(
            execution_id="exec1",
            workflow_id="wf1",
            status=WorkflowStatus.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

        data = execution.to_dict()

        self.assertEqual(data["execution_id"], "exec1")
        self.assertEqual(data["status"], "completed")

    def test_create_workflow_engine(self):
        """Test creating a workflow engine."""
        engine = create_workflow_engine(self.test_dir)

        self.assertIsInstance(engine, WorkflowEngine)
        self.assertEqual(engine.storage_dir, self.test_dir)

    def test_register_workflow(self):
        """Test registering a workflow."""
        engine = create_workflow_engine(self.test_dir)
        workflow = Workflow(
            id="wf1",
            name="Test",
            description="Test",
            steps=[],
        )

        engine.register_workflow(workflow)

        self.assertIn("wf1", engine.workflows)

    def test_get_workflow(self):
        """Test getting a registered workflow."""
        engine = create_workflow_engine(self.test_dir)
        workflow = Workflow(
            id="wf1",
            name="Test",
            description="Test",
            steps=[],
        )

        engine.register_workflow(workflow)
        found = engine.get_workflow("wf1")

        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Test")

    def test_execute_simple_workflow(self):
        """Test executing a simple workflow."""
        engine = create_workflow_engine(self.test_dir)

        step1 = WorkflowStep(
            id="step1",
            name="Step 1",
            action=lambda **kwargs: "result1",
        )

        workflow = Workflow(
            id="wf1",
            name="Test Workflow",
            description="Test",
            steps=[step1],
        )

        engine.register_workflow(workflow)
        execution = engine.execute("wf1")

        self.assertEqual(execution.status, WorkflowStatus.COMPLETED)
        self.assertIn("step1", execution.step_results)
        self.assertEqual(execution.step_results["step1"].status, StepStatus.COMPLETED)

    def test_execute_workflow_with_dependencies(self):
        """Test workflow with dependencies."""
        engine = create_workflow_engine(self.test_dir)

        execution_order = []

        step1 = WorkflowStep(
            id="step1",
            name="Step 1",
            action=lambda **kwargs: execution_order.append("step1"),
        )

        step2 = WorkflowStep(
            id="step2",
            name="Step 2",
            action=lambda **kwargs: execution_order.append("step2"),
            dependencies=["step1"],
        )

        workflow = Workflow(
            id="wf1",
            name="Test",
            description="Test",
            steps=[step2, step1],  # Note: step2 comes first but depends on step1
        )

        engine.register_workflow(workflow)
        execution = engine.execute("wf1")

        self.assertEqual(execution.status, WorkflowStatus.COMPLETED)
        self.assertEqual(execution_order, ["step1", "step2"])

    def test_execute_workflow_step_failure(self):
        """Test workflow with failing step."""
        engine = create_workflow_engine(self.test_dir)

        step1 = WorkflowStep(
            id="step1",
            name="Failing Step",
            action=lambda **kwargs: 1 / 0,  # Will raise ZeroDivisionError
            retry_count=0,
        )

        workflow = Workflow(
            id="wf1",
            name="Test",
            description="Test",
            steps=[step1],
        )

        engine.register_workflow(workflow)
        execution = engine.execute("wf1")

        self.assertEqual(execution.status, WorkflowStatus.FAILED)
        self.assertEqual(execution.step_results["step1"].status, StepStatus.FAILED)

    def test_execute_workflow_with_context(self):
        """Test workflow with context data."""
        engine = create_workflow_engine(self.test_dir)

        step1 = WorkflowStep(
            id="step1",
            name="Context Step",
            action=lambda **kwargs: kwargs.get("context", {}).get("key", "default"),
        )

        workflow = Workflow(
            id="wf1",
            name="Test",
            description="Test",
            steps=[step1],
        )

        engine.register_workflow(workflow)
        execution = engine.execute("wf1", context={"key": "value"})

        self.assertEqual(execution.status, WorkflowStatus.COMPLETED)
        self.assertEqual(execution.context["key"], "value")

    def test_list_executions(self):
        """Test listing executions."""
        engine = create_workflow_engine(self.test_dir)

        workflow = Workflow(
            id="wf1",
            name="Test",
            description="Test",
            steps=[WorkflowStep(id="s1", name="S1", action=lambda ctx: None)],
        )

        engine.register_workflow(workflow)
        engine.execute("wf1")
        engine.execute("wf1")

        executions = engine.list_executions()

        self.assertEqual(len(executions), 2)

    def test_execution_persistence(self):
        """Test saving and loading execution."""
        engine = create_workflow_engine(self.test_dir)

        step1 = WorkflowStep(
            id="step1",
            name="Step 1",
            action=lambda **kwargs: "output",
        )

        workflow = Workflow(
            id="wf1",
            name="Test",
            description="Test",
            steps=[step1],
        )

        engine.register_workflow(workflow)
        execution = engine.execute("wf1")

        # Load execution
        loaded = engine.load_execution(execution.execution_id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.execution_id, execution.execution_id)
        self.assertEqual(loaded.status, WorkflowStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
