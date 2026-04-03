"""Tests for devtools_integration module."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.devtools_integration import (
    ToolResult,
    ToolRunner,
    PytestRunner,
    RuffRunner,
    MypyRunner,
    UvRunner,
    DevToolsIntegration,
    create_devtools,
)


class TestDevToolsIntegration(unittest.TestCase):
    """Test cases for devtools integration."""

    def test_create_tool_result(self):
        """Test creating a tool result."""
        result = ToolResult(
            tool="pytest",
            success=True,
            exit_code=0,
            stdout="OK",
            stderr="",
        )

        self.assertEqual(result.tool, "pytest")
        self.assertTrue(result.success)

    def test_create_tool_runner(self):
        """Test creating a tool runner."""
        runner = ToolRunner()

        self.assertEqual(runner.cwd, Path.cwd())

    def test_create_pytest_runner(self):
        """Test creating pytest runner."""
        runner = PytestRunner()

        self.assertIsInstance(runner, ToolRunner)

    def test_create_ruff_runner(self):
        """Test creating ruff runner."""
        runner = RuffRunner()

        self.assertIsInstance(runner, ToolRunner)

    def test_create_mypy_runner(self):
        """Test creating mypy runner."""
        runner = MypyRunner()

        self.assertIsInstance(runner, ToolRunner)

    def test_create_uv_runner(self):
        """Test creating uv runner."""
        runner = UvRunner()

        self.assertIsInstance(runner, ToolRunner)

    def test_create_devtools_integration(self):
        """Test creating devtools integration."""
        devtools = create_devtools()

        self.assertIsInstance(devtools, DevToolsIntegration)
        self.assertIsInstance(devtools.pytest, PytestRunner)
        self.assertIsInstance(devtools.ruff, RuffRunner)
        self.assertIsInstance(devtools.mypy, MypyRunner)
        self.assertIsInstance(devtools.uv, UvRunner)

    @patch("subprocess.run")
    def test_run_command_success(self, mock_run):
        """Test running a command successfully."""
        mock_run.return_value = Mock(
            returncode=0, stdout="success", stderr=""
        )

        runner = ToolRunner()
        result = runner.run_command(["echo", "test"])

        self.assertTrue(result.success)
        self.assertEqual(result.exit_code, 0)

    @patch("subprocess.run")
    def test_run_command_failure(self, mock_run):
        """Test running a failing command."""
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="error"
        )

        runner = ToolRunner()
        result = runner.run_command(["test"])

        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 1)

    @patch("subprocess.run")
    def test_pytest_run_tests(self, mock_run):
        """Test running pytest."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        runner = PytestRunner()
        result = runner.run_tests()

        self.assertTrue(result.success)
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_pytest_run_with_coverage(self, mock_run):
        """Test running pytest with coverage."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        runner = PytestRunner()
        result = runner.run_tests(coverage=True)

        # Check that coverage flags were added
        call_args = mock_run.call_args[0][0]
        self.assertIn("--cov=src", call_args)

    @patch("subprocess.run")
    def test_ruff_check(self, mock_run):
        """Test running ruff check."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        runner = RuffRunner()
        result = runner.check()

        self.assertTrue(result.success)

    @patch("subprocess.run")
    def test_ruff_fix(self, mock_run):
        """Test running ruff fix."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        runner = RuffRunner()
        result = runner.fix()

        # Check that --fix flag was added
        call_args = mock_run.call_args[0][0]
        self.assertIn("--fix", call_args)

    @patch("subprocess.run")
    def test_ruff_format(self, mock_run):
        """Test running ruff format."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        runner = RuffRunner()
        result = runner.format()

        self.assertTrue(result.success)

    @patch("subprocess.run")
    def test_mypy_check(self, mock_run):
        """Test running mypy."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        runner = MypyRunner()
        result = runner.check()

        self.assertTrue(result.success)

    @patch("subprocess.run")
    def test_mypy_strict(self, mock_run):
        """Test running mypy with strict mode."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        runner = MypyRunner()
        result = runner.check(strict=True)

        # Check that --strict flag was added
        call_args = mock_run.call_args[0][0]
        self.assertIn("--strict", call_args)

    @patch("subprocess.run")
    def test_uv_install(self, mock_run):
        """Test running uv install."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        runner = UvRunner()
        result = runner.install(["requests"])

        self.assertTrue(result.success)

    @patch("subprocess.run")
    def test_devtools_run_all_checks(self, mock_run):
        """Test running all checks."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        devtools = DevToolsIntegration()
        results = devtools.run_all_checks()

        self.assertIn("ruff_check", results)
        self.assertIn("mypy", results)
        self.assertIn("pytest", results)

    @patch("subprocess.run")
    def test_devtools_fix_all(self, mock_run):
        """Test fixing all issues."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        devtools = DevToolsIntegration()
        results = devtools.fix_all()

        self.assertIn("ruff_fix", results)
        self.assertIn("ruff_format", results)

    def test_devtools_summary(self):
        """Test generating summary."""
        devtools = DevToolsIntegration()

        results = {
            "pytest": ToolResult(tool="pytest", success=True, exit_code=0, stdout="", stderr="", duration_ms=100),
            "ruff": ToolResult(tool="ruff", success=False, exit_code=1, stdout="", stderr="error", duration_ms=50),
        }

        summary = devtools.summary(results)

        self.assertIn("pytest", summary)
        self.assertIn("ruff", summary)
        self.assertIn("❌ Some checks failed", summary)


if __name__ == "__main__":
    unittest.main()
