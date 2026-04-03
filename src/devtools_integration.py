"""
Development tools integration for pytest, ruff, mypy, and uv.

Provides unified interface to:
- Run pytest with coverage
- Run ruff linting and formatting
- Run mypy type checking
- Manage dependencies with uv
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    """Result of a tool execution."""

    tool: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float = 0.0


class ToolRunner:
    """Base class for tool runners."""

    def __init__(self, cwd: Path | None = None):
        """
        Initialize tool runner.

        Args:
            cwd: Working directory
        """
        self.cwd = cwd or Path.cwd()

    def run_command(
        self,
        command: list[str],
        timeout: int = 60,
    ) -> ToolResult:
        """
        Run a command.

        Args:
            command: Command and arguments
            timeout: Timeout in seconds

        Returns:
            ToolResult
        """
        import time

        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            duration = (time.time() - start_time) * 1000

            return ToolResult(
                tool=command[0],
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=duration,
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                tool=command[0],
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
            )
        except FileNotFoundError:
            return ToolResult(
                tool=command[0],
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Tool not found: {command[0]}",
            )


class PytestRunner(ToolRunner):
    """Run pytest tests."""

    def run_tests(
        self,
        test_path: str | None = None,
        coverage: bool = False,
        verbose: bool = True,
        extra_args: list[str] | None = None,
    ) -> ToolResult:
        """
        Run pytest.

        Args:
            test_path: Optional test file or directory
            coverage: Enable coverage reporting
            verbose: Verbose output
            extra_args: Additional pytest arguments

        Returns:
            ToolResult
        """
        command = ["python", "-m", "pytest"]

        if verbose:
            command.append("-v")

        if coverage:
            command.extend(["--cov=src", "--cov-report=term-missing"])

        if test_path:
            command.append(test_path)

        if extra_args:
            command.extend(extra_args)

        return self.run_command(command, timeout=300)

    def run_specific_test(self, test_name: str) -> ToolResult:
        """Run a specific test by name."""
        return self.run_tests(extra_args=["-k", test_name])


class RuffRunner(ToolRunner):
    """Run ruff linter and formatter."""

    def check(self, path: str | None = None) -> ToolResult:
        """
        Run ruff check.

        Args:
            path: Optional file or directory to check

        Returns:
            ToolResult
        """
        command = ["ruff", "check"]

        if path:
            command.append(path)
        else:
            command.append("src")

        return self.run_command(command)

    def fix(self, path: str | None = None) -> ToolResult:
        """Run ruff check with auto-fix."""
        command = ["ruff", "check", "--fix"]

        if path:
            command.append(path)
        else:
            command.append("src")

        return self.run_command(command)

    def format(self, path: str | None = None, check_only: bool = False) -> ToolResult:
        """Run ruff format."""
        command = ["ruff", "format"]

        if check_only:
            command.append("--check")

        if path:
            command.append(path)
        else:
            command.append("src")

        return self.run_command(command)


class MypyRunner(ToolRunner):
    """Run mypy type checker."""

    def check(
        self,
        path: str | None = None,
        strict: bool = False,
        extra_args: list[str] | None = None,
    ) -> ToolResult:
        """
        Run mypy.

        Args:
            path: Optional file or directory
            strict: Enable strict mode
            extra_args: Additional mypy arguments

        Returns:
            ToolResult
        """
        command = ["mypy"]

        if strict:
            command.append("--strict")

        command.append(path or "src")

        if extra_args:
            command.extend(extra_args)

        return self.run_command(command, timeout=120)


class UvRunner(ToolRunner):
    """Run uv package manager."""

    def install(self, packages: list[str], dev: bool = False) -> ToolResult:
        """
        Install packages.

        Args:
            packages: Package names
            dev: Install as dev dependency

        Returns:
            ToolResult
        """
        command = ["uv", "pip", "install"]

        if dev:
            command.append("--dev")

        command.extend(packages)

        return self.run_command(command, timeout=120)

    def sync(self) -> ToolResult:
        """Sync dependencies from lock file."""
        command = ["uv", "pip", "sync"]
        return self.run_command(command, timeout=120)

    def lock(self) -> ToolResult:
        """Generate lock file."""
        command = ["uv", "pip", "compile", "pyproject.toml"]
        return self.run_command(command, timeout=60)


class DevToolsIntegration:
    """Unified interface for development tools."""

    def __init__(self, cwd: Path | None = None):
        """
        Initialize integration.

        Args:
            cwd: Working directory
        """
        self.cwd = cwd or Path.cwd()
        self.pytest = PytestRunner(cwd)
        self.ruff = RuffRunner(cwd)
        self.mypy = MypyRunner(cwd)
        self.uv = UvRunner(cwd)

    def run_all_checks(self) -> dict[str, ToolResult]:
        """
        Run all checks (lint, type, test).

        Returns:
            Dict of tool name to result
        """
        results = {}

        # Lint
        results["ruff_check"] = self.ruff.check()
        results["ruff_format"] = self.ruff.format(check_only=True)

        # Type check
        results["mypy"] = self.mypy.check()

        # Tests
        results["pytest"] = self.pytest.run_tests(coverage=True)

        return results

    def fix_all(self) -> dict[str, ToolResult]:
        """
        Fix all auto-fixable issues.

        Returns:
            Dict of tool name to result
        """
        results = {}

        # Fix linting issues
        results["ruff_fix"] = self.ruff.fix()

        # Format code
        results["ruff_format"] = self.ruff.format()

        return results

    def summary(self, results: dict[str, ToolResult]) -> str:
        """
        Generate summary report.

        Args:
            results: Tool results

        Returns:
            Summary string
        """
        lines = ["# Development Tools Summary", ""]

        for tool_name, result in results.items():
            status = "✅" if result.success else "❌"
            lines.append(f"{status} {tool_name}: Exit code {result.exit_code}")

            if not result.success and result.stderr:
                lines.append(f"  Error: {result.stderr[:200]}")

            lines.append(f"  Duration: {result.duration_ms:.0f}ms")

        # Overall status
        all_success = all(r.success for r in results.values())
        lines.append("")
        lines.append(f"Overall: {'✅ All checks passed' if all_success else '❌ Some checks failed'}")

        return "\n".join(lines)


def create_devtools(cwd: Path | None = None) -> DevToolsIntegration:
    """Create devtools integration."""
    return DevToolsIntegration(cwd)
