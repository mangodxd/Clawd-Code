"""
Diagnostic system for /doctor command.

Provides functionality to:
- Check environment (Python, dependencies, configuration)
- Check permissions (API keys, file access, network)
- Check performance (response time, token efficiency)
- Generate diagnostic reports
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DiagCheck:
    """Result of a single diagnostic check."""

    category: str
    name: str
    status: str  # "ok", "warning", "error"
    message: str
    details: dict[str, Any] | None = None


@dataclass
class DiagReport:
    """Complete diagnostic report."""

    checks: list[DiagCheck]

    def summary(self) -> dict[str, int]:
        """Get summary by status."""
        summary = {"ok": 0, "warning": 0, "error": 0}
        for check in self.checks:
            summary[check.status] += 1
        return summary

    def has_errors(self) -> bool:
        """Check if any errors."""
        return any(check.status == "error" for check in self.checks)

    def has_warnings(self) -> bool:
        """Check if any warnings."""
        return any(check.status == "warning" for check in self.checks)

    def as_markdown(self) -> str:
        """Render report as markdown."""
        lines = ["# Diagnostic Report", ""]

        summary = self.summary()
        lines.append("## Summary")
        lines.append(f"- ✅ OK: {summary['ok']}")
        lines.append(f"- ⚠️ Warnings: {summary['warning']}")
        lines.append(f"- ❌ Errors: {summary['error']}")
        lines.append("")

        # Group by category
        categories = {}
        for check in self.checks:
            if check.category not in categories:
                categories[check.category] = []
            categories[check.category].append(check)

        for category, checks in sorted(categories.items()):
            lines.append(f"## {category.title()}")
            lines.append("")

            for check in checks:
                icon = "✅" if check.status == "ok" else "⚠️" if check.status == "warning" else "❌"
                lines.append(f"{icon} **{check.name}**: {check.message}")

                if check.details:
                    for key, value in sorted(check.details.items()):
                        lines.append(f"  - {key}: {value}")
                lines.append("")

        return "\n".join(lines)


class Doctor:
    """Runs diagnostic checks."""

    def __init__(self):
        self.checks: list[DiagCheck] = []

    def run_all_checks(self) -> DiagReport:
        """Run all diagnostic checks."""
        self.checks = []

        # Environment checks
        self._check_python_version()
        self._check_platform()
        self._check_dependencies()

        # Permission checks
        self._check_api_keys()
        self._check_file_access()

        # Configuration checks
        self._check_configuration()

        return DiagReport(checks=self.checks)

    def _check_python_version(self) -> None:
        """Check Python version."""
        version = sys.version_info

        if version >= (3, 10):
            self.checks.append(
                DiagCheck(
                    category="Environment",
                    name="Python Version",
                    status="ok",
                    message=f"Python {version.major}.{version.minor}.{version.micro}",
                    details={"version": f"{version.major}.{version.minor}.{version.micro}"},
                )
            )
        else:
            self.checks.append(
                DiagCheck(
                    category="Environment",
                    name="Python Version",
                    status="error",
                    message=f"Python 3.10+ required, found {version.major}.{version.minor}",
                    details={"required": "3.10+", "found": f"{version.major}.{version.minor}"},
                )
            )

    def _check_platform(self) -> None:
        """Check platform information."""
        self.checks.append(
            DiagCheck(
                category="Environment",
                name="Platform",
                status="ok",
                message=f"{platform.system()} {platform.release()}",
                details={
                    "system": platform.system(),
                    "release": platform.release(),
                    "machine": platform.machine(),
                },
            )
        )

    def _check_dependencies(self) -> None:
        """Check key dependencies."""
        dependencies = ["anthropic", "openai", "zhipuai", "rich", "promptToolkit", "python-dotenv"]

        missing = []
        found = []

        for dep in dependencies:
            try:
                __import__(dep.replace("-", "_"))
                found.append(dep)
            except ImportError:
                missing.append(dep)

        if missing:
            self.checks.append(
                DiagCheck(
                    category="Environment",
                    name="Dependencies",
                    status="warning",
                    message=f"Missing {len(missing)} optional dependencies",
                    details={"missing": missing, "found": found},
                )
            )
        else:
            self.checks.append(
                DiagCheck(
                    category="Environment",
                    name="Dependencies",
                    status="ok",
                    message=f"All {len(found)} dependencies available",
                    details={"found": found},
                )
            )

    def _check_api_keys(self) -> None:
        """Check API key configuration."""
        import os

        keys = {
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "GLM_API_KEY": os.getenv("GLM_API_KEY"),
        }

        results = {}
        for key, value in keys.items():
            if value:
                results[key] = f"{value[:10]}..." if len(value) > 10 else "SET"
            else:
                results[key] = "NOT SET"

        set_count = sum(1 for v in keys.values() if v)
        total = len(keys)

        if set_count == 0:
            self.checks.append(
                DiagCheck(
                    category="Permissions",
                    name="API Keys",
                    status="error",
                    message="No API keys configured",
                    details=results,
                )
            )
        elif set_count < total:
            self.checks.append(
                DiagCheck(
                    category="Permissions",
                    name="API Keys",
                    status="warning",
                    message=f"{set_count}/{total} API keys configured",
                    details=results,
                )
            )
        else:
            self.checks.append(
                DiagCheck(
                    category="Permissions",
                    name="API Keys",
                    status="ok",
                    message=f"All {total} API keys configured",
                    details=results,
                )
            )

    def _check_file_access(self) -> None:
        """Check file system permissions."""
        test_paths = [
            Path.cwd(),
            Path.home() / ".claude",
            Path.cwd() / ".port_sessions",
        ]

        results = {}
        for test_path in test_paths:
            try:
                if test_path.exists():
                    # Test read/write
                    test_file = test_path / ".doctor_test"
                    test_file.write_text("test")
                    test_file.read_text()
                    test_file.unlink()
                    results[str(test_path)] = "read/write OK"
                else:
                    results[str(test_path)] = "not found"
            except Exception as e:
                results[str(test_path)] = f"error: {e}"

        error_count = sum(1 for v in results.values() if "error" in v)

        if error_count > 0:
            self.checks.append(
                DiagCheck(
                    category="Permissions",
                    name="File Access",
                    status="warning",
                    message=f"{error_count} path(s) have access issues",
                    details=results,
                )
            )
        else:
            self.checks.append(
                DiagCheck(
                    category="Permissions",
                    name="File Access",
                    status="ok",
                    message="All paths accessible",
                    details=results,
                )
            )

    def _check_configuration(self) -> None:
        """Check configuration files."""
        config_files = [
            Path.cwd() / ".claude" / "settings.json",
            Path.cwd() / ".claude" / "settings.local.json",
            Path.cwd() / "CLAUDE.md",
            Path.cwd() / "pyproject.toml",
        ]

        results = {}
        for config_file in config_files:
            results[config_file.name] = "found" if config_file.exists() else "not found"

        found_count = sum(1 for v in results.values() if v == "found")

        self.checks.append(
            DiagCheck(
                category="Configuration",
                name="Config Files",
                status="ok",
                message=f"{found_count}/{len(config_files)} config files found",
                details=results,
            )
        )


def run_doctor() -> DiagReport:
    """
    Run all diagnostic checks.

    Returns:
        DiagReport instance
    """
    doctor = Doctor()
    return doctor.run_all_checks()
